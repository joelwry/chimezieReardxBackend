from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ActivityViewSet, CustomLoginAPIView, CustomUserViewSet, PaymentViewSet, SignupView, SurveyTaskViewSet, TransactionViewSet, DashboardAPIView, VerifyDepositAPIView,CompleteTaskAPIView, getUserBalance, RewardViewSet, RewardTransferAPIView, DailyGrowthRateViewSet, DailyGrowthViewSet, WithdrawalViewSet
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


router = DefaultRouter()
router.register(r'surveys', SurveyTaskViewSet)
router.register(r'users', CustomUserViewSet, basename='users')
router.register(r'payments', PaymentViewSet, basename='payments')
# router.register(r'surveys', SurveyTaskViewSet, basename='surveys')
router.register(r'activities', ActivityViewSet, basename='activities')
router.register(r'transactions', TransactionViewSet, basename='transactions')
router.register(r'rewards', RewardViewSet, basename='rewards')
router.register(r'daily-growth-rates', DailyGrowthRateViewSet, basename='daily-growth-rates')
router.register(r'daily-growths', DailyGrowthViewSet, basename='daily-growths')
router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawals')
urlpatterns = router.urls
urlpatterns += [
    path("signup/", SignupView.as_view(), name="signup"),
    path('auth/login/', CustomLoginAPIView.as_view(), name='custom_login'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    path("verify-deposit/", VerifyDepositAPIView.as_view(), name="verify_deposit"),
    path("complete-task/", CompleteTaskAPIView.as_view(), name="complete_task"),
    path("user-balance/",getUserBalance, name='user-balance-alone'),
    path("transfer-rewards/", RewardTransferAPIView.as_view(), name="reward-transfer"),
]

'''
ENDPOINTS
/users/	GET	Get user info (read-only)
/payments/	CRUD	Fund wallet via crypto
/surveys/	CRUD	View available tasks
/activities/	CRUD	Mark tasks as completed

POST /auth/token/ → login with email/password (get access + refresh tokens)

POST /auth/token/refresh/ → refresh access token using refresh token
'''