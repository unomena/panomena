import sys
import copy

from django.db.models import Q
from django.contrib import messages
from django.shortcuts import render_to_response
from django.template import loader
from django.template import RequestContext
from django.utils.translation import ugettext
from django.views.generic import list_detail
from django.http import HttpResponse

class DefaultURL(object):
    def __call__(self, obj=None):
        if obj:
            try:
                return obj.get_absolute_url()
            except AttributeError:
                return ''
        else:
            return self
    
class GenericBase(object):
    def __init__(self, *args, **kwargs):
        self.params=kwargs
        self.params['view_modifier'] = None
        self.params['url_callable'] = None

    def __call__(self, request, *args, **kwargs):
        self.request = request
        view = copy.copy(self)
        
        # setup view params
        view.params = view._resolve_view_params(request, view.defaults, *args, **kwargs)
      
        # push the view through view modifier
        if view.params['extra_context'].has_key('view_modifier'):
            view_modifier = view.params['extra_context']['view_modifier']
            if view_modifier:
                if callable(view_modifier):
                    view_modifier = view_modifier(request=request, *args, **kwargs)
                    view.params['extra_context']['view_modifier'] = view_modifier
                view = view_modifier.modify(view)

        return view

    def get_url_callable(self, *args, **kwargs):
        return DefaultURL()

    def _resolve_view_params(self, request, defaults, *args, **kwargs):
        """
        Resolves view params with least ammount of resistance.
        Firstly check for params on urls passed args, then on class init args or members, 
        and lastly on class get methods .
        """
        params = copy.copy(defaults)
        params.update(self.params)
        params.update(kwargs)
        resolved_params = {}
        
        extra_context = {}
        for key in params:
            # grab from provided params. 
            value = params[key]
            
            # otherwise grab from existing params
            if value == None:
                value = self.params[key] if self.params.has_key(key) else None
            
            # otherwise grab from class method
            if value == None:
                value = getattr(self, 'get_%s' % key)(request, *args, **kwargs) if getattr(self, 'get_%s' % key, None) else None

            if key in defaults:
                resolved_params[key] = value
            else:
                extra_context[key] = value
        
        if extra_context:
            try:
                resolved_params['extra_context'].update(extra_context)
            except AttributeError:
                resolved_params['extra_context'] = extra_context

        return resolved_params
        
class GenericObjectList(GenericBase):
    defaults = {
        'queryset': None,
        'paginate_by': None, 
        'page':None,
        'allow_empty':True, 
        'template_name':None, 
        'template_loader':loader,
        'extra_context':None, 
        'context_processors':None, 
        'template_object_name':'object',
        'mimetype':None,
    }
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericObjectList, self).__call__(request, *args, **kwargs)
        
        # setup object_list params
        queryset=view.params['queryset']
        del view.params['queryset']

        # return object list generic view
        return list_detail.object_list(request, queryset=queryset, **view.params)
        
generic_object_list = GenericObjectList()
        
class GenericObjectFilterList(GenericObjectList):
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericObjectList, self).__call__(request, *args, **kwargs)

        # setup object_list params
        queryset=view.params['queryset']
        del view.params['queryset']
        
        # Filter
        for field in queryset.model._meta.fields:
            if field.name in view.params['extra_context'].keys():
                queryset = queryset.filter(Q(**{"%s__exact" % field.name : view.params['extra_context'][field.name]}))
        
        # return object list generic view
        return list_detail.object_list(request, queryset=queryset, **view.params)
        
generic_object_filter_list = GenericObjectFilterList()

class GenericObjectFilterOrderList(GenericObjectList):
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericObjectList, self).__call__(request, *args, **kwargs)
        
        # setup object_list params
        queryset=view.params['queryset']
        del view.params['queryset']
        
        if view.params['extra_context'].has_key('filter'):
            # Filter
            for field in view.params['extra_context']['filter'].keys():
                
                if view.params['extra_context']['filter'][field].has_key('operator'):
                    queryset = queryset.filter(Q(**{"%s__%s" % (field, view.params['extra_context']['filter'][field]['operator']) : view.params['extra_context']['filter'][field]['value']}))
                else:
                    queryset = queryset.filter(Q(**{"%s" % field : view.params['extra_context']['filter'][field]['value']}))
                    
        order_by = '-id'
        
        if request.GET.has_key('order_by'):
            order_by = request.GET['order_by']
            request.session['order_by_%s' % view.params['extra_context']['unique_session_key']] = order_by
        elif request.session.has_key('order_by_%s' % view.params['extra_context']['unique_session_key']):
            order_by = request.session['order_by_%s' % view.params['extra_context']['unique_session_key']]
                
        view.params['extra_context']['order_by'] = order_by
        
        queryset = queryset.order_by(order_by,'-id')
        
        request.session['full_queryset'] = queryset
        
        try:
            view.params['paginate_by'] =  int(request.POST.get('page_limit', request.session['page_limit']))
            request.session['page_limit'] = view.params['paginate_by']
        except:
            request.session['page_limit'] = kwargs['paginate_by']
            
        view.params['extra_context']['page_limit'] = request.session['page_limit']
        
        # return object list generic view
        return list_detail.object_list(request, queryset=queryset, **view.params)
        
generic_object_filter_order_list = GenericObjectFilterOrderList()

#==============================================================================
class GenericSearchForm(GenericBase):
    defaults = {
        'form_class': None,
        'form_args': None,
        'initial': None,
        'extra_context': None, 
        'template_name': None,
        'success_message': None,
        'filter_name': None,
    }
    
    def handle_valid(self, form=None, *args, **kwargs):
        """
        Called after the form has validated.
        """
        # Try and call handle_valid method of the form itself.
        if hasattr(form, 'handle_valid'):
            filter = form.handle_valid(*args, **kwargs)
            
        return filter
    
    def redirect(self, request, *args, **kwargs):
        """
        Redirect after successful form submission.
        Default behaviour is to not redirect and hence return the original view.
        """
        return None
    
    #--------------------------------------------------------------------------
    def get_form_args(self, *args, **kwargs):
        return {}
        
    #--------------------------------------------------------------------------
    def get_initial(self, request, *args, **kwargs):
        return {}
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericSearchForm, self).__call__(request, *args, **kwargs)

        self.form_class = view.params['form_class']
        self.form_args = view.params['form_args']
        self.template_name = view.params['template_name']
        self.success_message = view.params['success_message']
        self.filter_name = view.params['filter_name']

        kwargs['filter_on'] = False
        kwargs['filter_form'] = view.params['form_class']

        if self.form_class:
            if request.method == 'POST':
                
                if request.POST.has_key('clearFilter') and request.POST['clearFilter'] == 'True':
                    form = self.form_class(initial=self.get_initial(request=request, *args, **kwargs), **self.form_args)
                    kwargs['filter_on'] = False
                    request.session['%s_filter_on' % self.filter_name] = False
                    request.session[self.filter_name] = {}
                    
                else:
                    if request.POST.has_key('clearFilter'):
                        form = self.form_class(data=request.POST, files=request.FILES, **self.form_args)
                        request.session['%s_data' % self.filter_name] = request.POST
                    else:
                        if request.session.has_key('%s_filter_on' % self.filter_name) and request.session['%s_filter_on' % self.filter_name]:
                            data = request.session['%s_data' % self.filter_name]
                            form = self.form_class(data=data, files=request.FILES, **self.form_args)
                        else:
                            form = self.form_class(initial=self.get_initial(request=request, *args, **kwargs), **self.form_args)
                        
                    if form.is_valid():
                        request.session[self.filter_name] = self.handle_valid(form=form, request=request, *args, **kwargs)
                        if request.session[self.filter_name]:
                            kwargs['filter_on'] = True
                        else:
                            kwargs['filter_on'] = False
                            
                        request.session['%s_filter_on' % self.filter_name] = kwargs['filter_on']
                    
            else:
                if request.session.has_key('%s_filter_on' % self.filter_name) and request.session['%s_filter_on' % self.filter_name]:
                    data = request.session['%s_data' % self.filter_name]
                    form = self.form_class(data=data, files=request.FILES, **self.form_args)
                    
                    if form.is_valid():
                        request.session[self.filter_name] = self.handle_valid(form=form, request=request, *args, **kwargs)
                        if request.session[self.filter_name]:
                            kwargs['filter_on'] = True
                        else:
                            kwargs['filter_on'] = False
                            
                        request.session['%s_filter_on' % self.filter_name] = kwargs['filter_on']
                else:
                    form = self.form_class(initial=self.get_initial(request=request, *args, **kwargs), **self.form_args)
       
            kwargs['filter_form'] = form
        else:
            kwargs['filter_form'] = None
            request.session[self.filter_name] = {}
        
        try:
            kwargs['filter'] = request.session[self.filter_name]
        except:
            kwargs['filter'] = {}
        
        return generic_object_filter_order_list(request, *args, **kwargs)
        
generic_search_form = GenericSearchForm()

class GenericObjectDetail(GenericBase):
    defaults = {
        'queryset': None,
        'object_id': None, 
        'slug': None,
        'slug_field':'slug', 
        'template_name_field':None,
        'template_name':None, 
        'template_loader':loader,
        'extra_context':None, 
        'context_processors':None, 
        'template_object_name':'object',
        'mimetype':None,
    }
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericObjectDetail, self).__call__(request, *args, **kwargs)
        
        # setup object_list params
        queryset=view.params['queryset']
        del view.params['queryset']

        # return object list generic view
        return list_detail.object_detail(request, queryset=queryset, **view.params)
        
generic_object_detail = GenericObjectDetail()

class GenericForm(GenericBase):
    defaults = {
        'form_class': None,
        'form_args': None,
        'initial': None,
        'extra_context': None, 
        'template_name': None,
        'success_message': None,
    }
    
    def handle_valid(self, form=None, *args, **kwargs):
        """
        Called after the form has validated.
        """
        # Take a chance and try save a subclass of a ModelForm.
        if hasattr(form, 'save'):
            form.save()
        # Also try and call handle_valid method of the form itself.
        if hasattr(form, 'handle_valid'):
            form.handle_valid(*args, **kwargs)
    
    def redirect(self, request, *args, **kwargs):
        """
        Redirect after successful form submission.
        Default behaviour is to not redirect and hence return the original view.
        """
        return None
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericForm, self).__call__(request, *args, **kwargs)

        self.form_class = view.params['form_class']
        self.form_args = view.params['form_args'] or {}
        self.initial = view.params['initial']
        self.template_name = view.params['template_name']
        self.success_message = view.params['success_message']

        if request.method == 'POST':
            form = self.form_class(data=request.POST, files=request.FILES, **self.form_args)
            if form.is_valid():
                self.handle_valid(form=form, request=request, *args, **kwargs)
                if self.success_message:
                    msg = ugettext(self.success_message)
                    messages.success(request, msg, fail_silently=True)
                redirect = self.redirect(request, *args, **kwargs)
                if redirect:
                    return redirect
        else:
            form = self.form_class(initial=self.initial, **self.form_args)
    
        context = RequestContext(request, {})
        context.update({
            'form': form,
        })
        context.update(view.params['extra_context'])
        return render_to_response(self.template_name, context)
        
generic_form_view = GenericForm()

class GenericList(GenericBase):
    defaults = {
        'callback': None,
        'callback_kwargs': None,
        'template_name': None, 
        'template_name_field': None,
        'template_loader': loader,
        'template_object_name': 'object_list',
        'context_processors': None, 
        'extra_context': None, 
        'mimetype': None,
    }
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericList, self).__call__(request, *args, **kwargs)
        
        # return generic detail generic view
        return self.generic_list(request, view.params.pop('callback'), **view.params)
    
    def generic_list(self, request, callback, **kwargs):
        """
        Generic list of a non-QuerySet objects, yielded by calling the klass 
        method and passing method_kwargs  
        """
        template_name = kwargs['template_name']
        template_name_field = kwargs['template_name_field']
        template_loader = kwargs['template_loader']
        template_object_name = kwargs['template_object_name']
        context_processors = kwargs['context_processors']
        mimetype = kwargs['mimetype']
        
        extra_context = kwargs.get('extra_context', {})  or {}
        callback_args = kwargs.get('callback_args', ())  or ()
        callback_kwargs = kwargs.get('callback_kwargs', {})  or {}
            
        if not callable(callback):
            mod_name = callback.split('.')[:-1]
            __import__(mod_name)
            callback = getattr(sys.modules[mod_name], callback.split('.')[-1])
        
        object_list = callback(*callback_args, **callback_kwargs)
        
        if hasattr(self, 'callback_results_processor') and \
            callable(getattr(self, 'callback_results_processor')):
            getattr(self, 'callback_results_processor')(request, object_list, **kwargs)
        
        if template_name_field:
            template_name_list = [getattr(object_list, template_name_field), template_name]
            t = template_loader.select_template(template_name_list)
        else:
            t = template_loader.get_template(template_name)
        c = RequestContext(request, {template_object_name: object_list}, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c), mimetype=mimetype)
        return response
            
generic_list = GenericList()

class GenericDetail(GenericBase):
    defaults = {
        'callback': None,
        'callback_kwargs': None,
        'template_name': None, 
        'template_name_field': None,
        'template_loader': loader,
        'template_object_name': 'object',
        'context_processors': None, 
        'extra_context': None, 
        'mimetype': None,
    }
    
    def __call__(self, request, *args, **kwargs):
        # generate our view via genericbase
        view = super(GenericDetail, self).__call__(request, *args, **kwargs)
        
        # return generic detail generic view
        return self.generic_detail(request, view.params.pop('callback'), **view.params)
    
    def generic_detail(self, request, callback, **kwargs):
        """
        Generic detail of a non-QuerySet object, yielded by calling the klass 
        method and passing method_kwargs  
        """
        template_name = kwargs['template_name']
        template_name_field = kwargs['template_name_field']
        template_loader = kwargs['template_loader']
        template_object_name = kwargs['template_object_name']
        context_processors = kwargs['context_processors']
        mimetype = kwargs['mimetype']
        
        extra_context = kwargs.get('extra_context', {})  or {}
        callback_args = kwargs.get('callback_args', ())  or ()
        callback_kwargs = kwargs.get('callback_kwargs', {})  or {}
            
        if not callable(callback):
            mod_name = callback.split('.')[:-1]
            __import__(mod_name)
            callback = getattr(sys.modules[mod_name], callback.split('.')[-1])
        
        obj = callback(*callback_args, **callback_kwargs)
        
        if hasattr(self, 'callback_results_processor') and \
            callable(getattr(self, 'callback_results_processor')):
            getattr(self, 'callback_results_processor')(request, obj, **kwargs)
        
        if template_name_field:
            template_name_list = [getattr(obj, template_name_field), template_name]
            t = template_loader.select_template(template_name_list)
        else:
            t = template_loader.get_template(template_name)
        c = RequestContext(request, {template_object_name: obj}, context_processors)
        for key, value in extra_context.items():
            if callable(value):
                c[key] = value()
            else:
                c[key] = value
        response = HttpResponse(t.render(c), mimetype=mimetype)
        return response
            
generic_detail = GenericDetail()
