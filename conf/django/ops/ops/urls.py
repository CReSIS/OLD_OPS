from django.urls import path
import ops.views

# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    # Examples:
    # url(r'^$', 'ops.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    # url(r'^admin/', include(admin.site.urls)),
    # OPS NAMING CONVENTIONS
    # [ACTION]/[TABLE]/[*] -> ops.views.actionTable*
    # UTILITY VIEWS
    path("login/user", ops.views.loginUser),
    path("logout/user", ops.views.logoutUser),
    path("create/user", ops.views.createUser),
    path("query", ops.views.query),
    path("updateMaterializedView", ops.views.updateMaterializedView),
    path("profile", ops.views.profile),
    path("analyze", ops.views.analyze),
    path("alter/user/permissions", ops.views.alterUserPermissions),
    # INPUT VIEWS
    path("create/path", ops.views.createPath),
    path("alter/path/resolution", ops.views.alterPathResolution),
    path("create/layer", ops.views.createLayer),
    path("delete/layer", ops.views.deleteLayer),
    path("create/layer/points", ops.views.createLayerPoints),
    path("delete/layer/points", ops.views.deleteLayerPoints),
    path("delete/bulk", ops.views.deleteBulk),
    path("delete/bulk", ops.views.deleteBulk),
    path("release/layer/group", ops.views.releaseLayerGroup),
    # OUPUT VIEWS
    path("get/path", ops.views.getPath),
    path("get/frame/closest", ops.views.getFrameClosest),
    path("get/layers", ops.views.getLayers),
    path("get/layer/points", ops.views.getLayerPoints),
    path("get/layer/points/csv", ops.views.getLayerPointsCsv),
    path("get/layer/points/kml", ops.views.getLayerPointsKml),
    path("get/layer/points/mat", ops.views.getLayerPointsMat),
    path("get/layer/points/netcdf", ops.views.getLayerPointsNetcdf),
    path("get/system/info", ops.views.getSystemInfo),
    path("get/segment/info", ops.views.getSegmentInfo),
    path("get/crossovers", ops.views.getCrossovers),
    path("get/crossovers/report", ops.views.getCrossoversReport),
    path("get/frame/search", ops.views.getFrameSearch),
    path("get/initial/data", ops.views.getInitialData),
    path("get/user/profile/data", ops.views.getUserProfileData),
    path("get/frame/polygon", ops.views.getFramesWithinPolygon),
    path("get/point/polygon", ops.views.getPointsWithinPolygon),
]
