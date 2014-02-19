from django.conf.urls import patterns, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'ops.views.home', name='home'),
    # url(r'^ops/', include('ops.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    
    # OPS CONVENTIONS [ACTION]/[OBJECT]/[*]
    
    # UTILITY FUNCTIONS
    url(r'^query$','ops.views.query'),
    url(r'^profile$','ops.views.profile'),
    url(r'^tables/analyze$','ops.views.tables_analyze'),
    
    
    # INPUT FUNCTIONS
    url(r'^create/path$','ops.views.create_path'),
    url(r'^create/layer$','ops.views.create_layer'),
    url(r'^delete/layer$','ops.views.delete_layer'),
    url(r'^create/layer/points$','ops.views.create_layer_points'),
    url(r'^delete/layer/points$','ops.views.delete_layer_points'),
    url(r'^delete/bulk$','ops.views.bulk_delete'),

    # OUTPUT FUNCTIONS
    url(r'^get/path$','ops.views.get_path'),
    url(r'^get/closest/point$','ops.views.get_closest_point'),
    url(r'^get/closest/frame$','ops.views.get_closest_frame'),    
    url(r'^get/layers$','ops.views.get_layers'),
    url(r'^get/layer/points$','ops.views.get_layer_points'),
    url(r'^get/layer/points/csv$','ops.views.get_layer_points_csv'),
    url(r'^get/layer/points/kml$','ops.views.get_layer_points_kml'),
    url(r'^get/system/info$','ops.views.get_system_info'),
    url(r'^get/segment/info$','ops.views.get_segment_info'),
    url(r'^get/crossover/error','ops.views.get_crossover_error'),
    url(r'^search/frames$','ops.views.search_frames'),
    url(r'^get/initial/data$','ops.views.get_initial_data'),
	
	# OUTPUT FUNCTIONS (EXT)
	url(r'^get/system/info/ext$','ops.views.get_system_info_ext'),
)