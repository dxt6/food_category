from django.urls import path
from . import views

urlpatterns = [
    path("", views.demo_home, name="demo_home"),
    path("vision/", views.vision_demo, name="vision_demo"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/categories/", views.category_list, name="category_list"),
    path("admin-panel/categories/add/", views.category_add, name="category_add"),
    path("admin-panel/categories/<str:pk>/delete/", views.category_delete, name="category_delete"),
    path("admin-panel/samples/", views.sample_list, name="sample_list"),
    path("admin-panel/samples/add/", views.sample_add, name="sample_add"),
    path("admin-panel/models/", views.model_manager, name="model_manager"),
    path("admin-panel/models/train/<str:name>/", views.model_train, name="model_train"),
    path("admin-panel/models/default/<str:name>/", views.model_set_default, name="model_set_default"),
    path("admin-panel/records/", views.record_list, name="record_list"),
    path("admin-panel/records/export/", views.record_export, name="record_export"),
    path("admin-panel/vision/", views.vision_record_list, name="vision_record_list"),
    path("admin-panel/vision/export/", views.vision_record_export, name="vision_record_export"),
    path("admin-panel/vision/model/", views.vision_model_manager, name="vision_model_manager"),
    path("admin-panel/vision/prepare/", views.vision_prepare_dataset, name="vision_prepare_dataset"),
    path("admin-panel/users/", views.user_manager, name="user_manager"),
    path("admin-panel/users/<int:pk>/role/", views.user_role, name="user_role"),
]
