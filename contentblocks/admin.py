'''
Created on 19 Jul 2011

@author: euan
'''
from django.contrib import admin

from panya.admin import PublisherModelAdmin

from contentblocks.models import ContentBlock, PlainTextBlock

#==============================================================================
class ContentBlockAdmin(PublisherModelAdmin):
    list_display = ('name', 'key', 'state',)
    list_filter = ('state',)
    fieldsets = (
                 (None, {'fields': ('key', 'name', 'content', )
                         }),
                 )

admin.site.register(ContentBlock, ContentBlockAdmin)
admin.site.register(PlainTextBlock)