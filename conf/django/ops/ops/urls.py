from django.conf.urls import patterns, url #,include

#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'ops.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    #url(r'^admin/', include(admin.site.urls)),
	
	# OPS NAMING CONVENTIONS
	# [ACTION]/[TABLE]/[*] -> ops.views.actionTable*
	
	# UTILITY VIEWS
	url(r'^login/user$','ops.views.loginUser'),
	url(r'^logout/user$','ops.views.logoutUser'),
	url(r'^create/user$','ops.views.createUser'),
	url(r'^query$','ops.views.query'),
	url(r'^profile$','ops.views.profile'),
	url(r'^analyze$','ops.views.analyze'),
	
	# INPUT VIEWS
	url(r'^create/path$','ops.views.createPath'),
	url(r'^create/layer$','ops.views.createLayer'),
	url(r'^delete/layer$','ops.views.deleteLayer'),
	url(r'^create/layer/points$','ops.views.createLayerPoints'),
	url(r'^delete/layer/points$','ops.views.deleteLayerPoints'),
	url(r'^delete/bulk$','ops.views.deleteBulk'),
	url(r'^delete/bulk$','ops.views.deleteBulk'),
	url(r'^release/layer/group$','ops.views.releaseLayerGroup'),
	
	# OUPUT VIEWS
	url(r'^get/path$','ops.views.getPath'),
	url(r'^get/frame/closest$','ops.views.getFrameClosest'),
	url(r'^get/layers$','ops.views.getLayers'),
	url(r'^get/layer/points$','ops.views.getLayerPoints'),
	url(r'^get/layer/points/csv$','ops.views.getLayerPointsCsv'),
	url(r'^get/layer/points/kml$','ops.views.getLayerPointsKml'),
	url(r'^get/layer/points/mat$','ops.views.getLayerPointsMat'),
	url(r'^get/layer/points/netcdf$','ops.views.getLayerPointsNetcdf'),
	url(r'^get/system/info$','ops.views.getSystemInfo'),
	url(r'^get/segment/info$','ops.views.getSegmentInfo'),
	url(r'^get/crossovers$','ops.views.getCrossovers'),
    url(r'^get/crossovers/report$','ops.views.getCrossoversReport'),
	url(r'^get/frame/search$','ops.views.getFrameSearch'),
	url(r'^get/initial/data$','ops.views.getInitialData'),
	url(r'^get/user/profile/data$','ops.views.getUserProfileData'),
)
