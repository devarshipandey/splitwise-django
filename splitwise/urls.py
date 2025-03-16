from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from splitwise import views

urlpatterns = [
    path('createGroup', views.CreateGroupApiView.as_view()),
    path('createExpense', views.CreateExpenseApiView.as_view()),
    path('createUser', views.UserProfileApiView.as_view()),
    path('addUserToGroup', views.AddUserToGroupApiView.as_view()),
    path('showGroupMembers', views.ShowGroupMembersApiView.as_view()),
    path('userDetails', views.ShowUserDetailsApiView.as_view()),
    path('addExpense', views.CreateExpenseApiView.as_view()),
    path('groupDetails', views.ShowGroupDetailsApiView.as_view()),
    path('deleteUser', views.DeleteUserApiView.as_view()),
    path('deleteGroup', views.DeleteGroupApiView.as_view()),
    path('recordPayment', views.RecordPaymentApiView.as_view()),

     # Frontend URLs
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('groups/create/', views.create_group, name='create-group'),
    path('groups/<uuid:group_id>/', views.group_detail, name='group-detail'),
    path('expenses/create/', views.create_expense, name='create-expense'),
    path('profile/', views.user_profile, name='user-profile'),
    path('users/', views.user_management, name='user-management'),
    path('users/delete/<uuid:user_id>/', views.delete_user, name='delete-user'),
    path('record-payment/', views.record_payment, name='record-payment'),
    path('groups/delete/<uuid:group_id>/', views.delete_group, name='delete-group'),
    path('users/create/', views.create_user, name='create-user'),
    path('static-test/', views.static_test, name='static-test'),
    path('api/debts/', views.UserDebtsApiView.as_view(), name='user-debts'),
    path('record-payment/', views.RecordPaymentApiView.as_view(), name='record-payment'),
    path('settle-debt/', views.settle_debt, name='settle-debt'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)