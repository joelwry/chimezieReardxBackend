from rest_framework import viewsets, status, serializers
from .models import Activity, Payment, SurveyTask,CustomUser, Transaction, Reward, DailyGrowthRate, DailyGrowth, Withdrawal
from .serializers import ActivitySerializer, PaymentSerializer, SurveyTaskSerializer, CustomUserSerializer, TransactionSerializer, DashboardSerializer, RewardSerializer, DailyGrowthRateSerializer, DailyGrowthSerializer, WithdrawalSerializer
from rest_framework.permissions import IsAuthenticated,IsAuthenticatedOrReadOnly,AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import requests
import json
from decimal import Decimal
from rest_framework.decorators import api_view, permission_classes, action

from decouple import config

# Your receiving wallet address (must match the network)
TRON_RECEIVER_ADDRESS = config("TRON_RECEIVER_ADDRESS")
# Optional but recommended: API key from TronGrid.io
TRONGRID_API_KEY = config("TRONGRID_API_KEY", default=None)
TRON_NODE=config("TRON_NODE")
TRON_USDT_ADDRESS = config("TRON_USDT_CONTRACT_ADDRESS")

class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    '''
    Only read-only for users here to prevent exposure of sensitive write endpoints.
    '''
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

class SurveyTaskViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SurveyTask.objects.all()
    serializer_class = SurveyTaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(customer=self.request.user) # type: ignore

    def perform_create(self, serializer : PaymentSerializer ):
        serializer.save(customer=self.request.user)

class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Activity.objects.filter(customer=self.request.user)
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task__id=task_id)
        print(list(queryset))
        return queryset

    def perform_create(self, serializer):
        task = serializer.validated_data['task']
        reward = task.reward_amount if task.is_active else 0
        serializer.save(
            customer=self.request.user,
            reward_earned=reward,
            completed=True,
            completed_at=now()
        )
        # Optional: credit reward to user wallet
        user : CustomUser = self.request.user
        user.balance += reward
        user.save()

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(customer=self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

class RewardViewSet(viewsets.ModelViewSet):
    serializer_class = RewardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Reward.objects.filter(user=self.request.user)

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CustomUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Signup successful",
                "user": CustomUserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CustomLoginAPIView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "Please provide both username and password."},
                            status=status.HTTP_400_BAD_REQUEST)
        
        user = CustomUser.objects.filter(username=username).first()

        user  = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                return Response({"detail": "Account is inactive."},
                                status=status.HTTP_403_FORBIDDEN)

            refresh = RefreshToken.for_user(user)

            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "balance": user.balance,
                }
            })

        return Response({"detail": "Invalid credentials."},
                        status=status.HTTP_401_UNAUTHORIZED)

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # User balance
        user_balance = user.balance
        # Tasks completed
        tasks_completed = Activity.objects.filter(customer=user, completed=True).count()
        # Available tasks
        completed_task_ids = Activity.objects.filter(customer=user).values_list('task_id', flat=True)
        available_tasks_qs = SurveyTask.objects.filter(is_active=True).exclude(id__in=completed_task_ids)
        available_tasks = available_tasks_qs.count()
        # Balance overview (simulate daily balance from first deposit to today)
        first_payment = Payment.objects.filter(customer=user, status='confirmed').order_by('created_at').first()
        if first_payment:
            start_date = first_payment.created_at.date()
        else:
            start_date = timezone.now().date() - timedelta(days=6)
        today = timezone.now().date()
        days = (today - start_date).days + 1
        # For demo, just use current balance for all days
        balance_overview = [
            {"date": (start_date + timedelta(days=i)).isoformat(), "balance": float(user_balance)}
            for i in range(days)
        ]
        # Available tasks list (up to 5)
        available_tasks_list = available_tasks_qs[:5]
        # Recent activity (up to 5)
        recent_activity = Activity.objects.filter(customer=user).order_by('-completed_at')[:5]
        data = {
            "user_balance": user_balance,
            "tasks_completed": tasks_completed,
            "available_tasks": available_tasks,
            "balance_overview": balance_overview,
            "available_tasks_list": available_tasks_list,
            "recent_activity": recent_activity,
        }
        serializer = DashboardSerializer(data)
        return Response(serializer.data)

# New API endpoint in views.py
class CompleteTaskAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        task_id = request.data.get('task_id')
        amount = request.data.get('amount')  # For lock/invest tasks
        period = request.data.get('period')  # For lock/invest tasks
        reward = request.data.get('reward')  # Instant reward
        try:
            task = SurveyTask.objects.get(id=task_id, is_active=True)
            user = request.user
            # Check if user already completed this task
            if Activity.objects.filter(customer=user, task=task).exists():
                return Response({"error": "Task already completed"}, status=400)
            # Handle different task types
            if task.type in ['lock', 'invest']:
                return self._handle_lock_invest_task(user, task, amount, period, reward)
            elif task.type == 'deposit':
                return self._handle_deposit_task(user, task, amount, reward)
            elif task.type == 'link':
                return self._handle_link_task(user, task, reward)
            else:
                return Response({"error": "Unsupported task type"}, status=400)
        except SurveyTask.DoesNotExist:
            return Response({"error": "Task not found"}, status=404)
    
    def _handle_lock_invest_task(self, user, task, amount, period, reward):
        if not amount or not period:
            return Response({"error": "Amount and period are required"}, status=400)
        if user.balance < Decimal(amount):
            return Response({
                "error": "Insufficient wallet balance",
                "required": float(amount),
                "available": float(user.balance),
                "action": "fund_wallet"
            }, status=400)
        # Deduct from balance
        user.balance -= Decimal(amount)
        user.save()
        # Add instant reward to Reward model
        if reward:
            reward_obj, _ = Reward.objects.get_or_create(user=user)
            reward_obj.total_reward += Decimal(reward)
            reward_obj.save()
        # Calculate rate and return_date
        rate = Decimal(reward) / Decimal(amount) * 100 if reward and amount else None
        start_date = timezone.now()
        return_date = start_date + timedelta(days=30*int(period))  # period in months
        # Create activity record
        Activity.objects.create(
            customer=user,
            task=task,
            completed=True,
            reward_earned=reward or task.reward_amount,
            completed_at=start_date,
            amount=Decimal(amount),
            rate=rate,
            start_date=start_date,
            return_date=return_date,
            is_returned=False
        )
        # Create transaction for lock/invest
        Transaction.objects.create(
            customer=user,
            type=task.type,
            amount=Decimal(amount),
            reference=f"{task.type.capitalize()} for task: {task.title}"
        )
        # Create transaction for reward
        if reward:
            Transaction.objects.create(
                customer=user,
                type='earning',
                amount=Decimal(reward),
                reference=f"Instant reward for task: {task.title}"
            )
        # Placeholder: ROI payout logic should be implemented as a management command or scheduled job
        # to process matured activities and credit ROI/principal to user wallet.
        return Response({
            "message": "Task completed successfully",
            "locked_or_invested_amount": float(amount),
            "reward_earned": float(reward or task.reward_amount),
            "new_balance": float(user.balance)
        })

    def _handle_deposit_task(self, user, task, amount, reward):
        if not amount:
            return Response({"error": "Amount is required"}, status=400)
        if user.balance < Decimal(amount):
            return Response({
                "error": "Insufficient wallet balance",
                "required": float(amount),
                "available": float(user.balance),
                "action": "fund_wallet"
            }, status=400)
        # Deduct from balance
        user.balance -= Decimal(amount)
        user.save()
        # Add instant reward to Reward model
        if reward:
            reward_obj, _ = Reward.objects.get_or_create(user=user)
            reward_obj.total_reward += Decimal(reward)
            reward_obj.save()
        # Calculate rate and return_date (if needed)
        rate = Decimal(reward) / Decimal(amount) * 100 if reward and amount else None
        start_date = timezone.now()
        return_date = start_date + timedelta(days=30)  # Default 1 month for deposit
        # Create activity record
        Activity.objects.create(
            customer=user,
            task=task,
            completed=True,
            reward_earned=reward or task.reward_amount,
            completed_at=start_date,
            amount=Decimal(amount),
            rate=rate,
            start_date=start_date,
            return_date=return_date,
            is_returned=False
        )
        # Create transaction for deposit
        Transaction.objects.create(
            customer=user,
            type='deposit',
            amount=Decimal(amount),
            reference=f"Deposit for task: {task.title}"
        )
        # Create transaction for reward
        if reward:
            Transaction.objects.create(
                customer=user,
                type='earning',
                amount=Decimal(reward),
                reference=f"Instant reward for task: {task.title}"
            )
        # Placeholder: ROI payout logic should be implemented as a management command or scheduled job
        # to process matured activities and credit ROI/principal to user wallet.
        return Response({
            "message": "Deposit task completed successfully",
            "deposited_amount": float(amount),
            "reward_earned": float(reward or task.reward_amount),
            "new_balance": float(user.balance)
        })

    def _handle_link_task(self, user, task, reward):
        # Add instant reward to Reward model
        if reward:
            reward_obj, _ = Reward.objects.get_or_create(user=user)
            reward_obj.total_reward += Decimal(reward)
            reward_obj.save()
        # Create activity record
        Activity.objects.create(
            customer=user,
            task=task,
            completed=True,
            reward_earned=reward or task.reward_amount,
            completed_at=timezone.now()
        )
        # Create transaction for reward
        if reward:
            Transaction.objects.create(
                customer=user,
                type='earning',
                amount=Decimal(reward),
                reference=f"Link share reward for task: {task.title}"
            )
        return Response({
            "message": "Link task completed successfully",
            "reward_earned": float(reward or task.reward_amount),
            "new_balance": float(user.balance)
        })

class VerifyDepositAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tx_hash = request.data.get('tx_hash')
        naira_amount = request.data.get('naira_amount')
        
        if not tx_hash or not naira_amount:
            return Response({
                "error": "Transaction hash and Naira amount are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Verify transaction on TronGrid
            tron_grid_url = f"https://api.trongrid.io/v1/transactions/{tx_hash}"
            headers = {
                "Accept": "application/json",
                "TRON-PRO-API-KEY": "YOUR_TRONGRID_API_KEY"  # Get from https://www.trongrid.io/
            }
            
            response = requests.get(tron_grid_url, headers=headers)
            
            if response.status_code != 200:
                return Response({
                    "error": "Failed to verify transaction"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tx_data = response.json()
            
            # Check if transaction is confirmed
            if not tx_data.get('confirmed'):
                return Response({
                    "error": "Transaction not yet confirmed"
                }, status=status.HTTP_400_BAD_REQUEST)
          
            # Verify it's a USDT transfer to our address
            contract_address = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT contract on Tron
            our_address = "YOUR_TRON_USDT_ADDRESS"  # Your wallet address
            
            # Check if this transaction already exists
            existing_payment = Payment.objects.filter(tx_hash=tx_hash).first()
            if existing_payment:
                return Response({
                    "error": "Transaction already processed"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # For demo purposes, assume verification succeeds
            # In production, you'd parse the transaction data to verify:
            # - It's a USDT transfer
            # - It's to your address
            # - The amount matches expected USDT amount
            
            # Create payment record
            payment = Payment.objects.create(
                customer=request.user,
                amount=Decimal(naira_amount),
                tx_hash=tx_hash,
                status='confirmed'
            )
            
            # Credit user balance
            user = request.user
            user.balance += Decimal(naira_amount)
            user.save()
            
            # Create transaction record
            Transaction.objects.create(
                customer=request.user,
                type='funding',
                amount=Decimal(naira_amount),
                reference=f"USDT deposit - {tx_hash[:8]}..."
            )
            
            return Response({
                "message": "Deposit verified and credited successfully",
                "amount": naira_amount,
                "new_balance": float(user.balance)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"Verification failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# other simple view 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getUserBalance(request):
    user = request.user
    user_balance = user.balance
    return Response({
        'balance': user_balance
    })

class RewardTransferAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            reward_obj = Reward.objects.get(user=user)
        except Reward.DoesNotExist:
            return Response({"error": "No reward to transfer."}, status=status.HTTP_400_BAD_REQUEST)
        if reward_obj.total_reward <= 0:
            return Response({"error": "No reward to transfer."}, status=status.HTTP_400_BAD_REQUEST)
        amount = reward_obj.total_reward
        user.balance += amount
        reward_obj.total_reward = 0
        user.save()
        reward_obj.save()
        return Response({
            "message": "Reward transferred successfully.",
            "amount": float(amount),
            "new_balance": float(user.balance)
        })

# --- Daily Growth Rate ViewSet ---
class DailyGrowthRateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyGrowthRate.objects.all()
    serializer_class = DailyGrowthRateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

# --- Daily Growth ViewSet ---
class DailyGrowthViewSet(viewsets.ModelViewSet):
    serializer_class = DailyGrowthSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DailyGrowth.objects.filter(user=self.request.user)
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by('-activated_date')

    def perform_create(self, serializer):
        user = self.request.user
        plan_id = self.request.data.get('plan_id')
        amount = self.request.data.get('amount')
        
        if not plan_id or not amount:
            raise serializers.ValidationError({'detail': 'Plan and amount are required.'})
        
        try:
            plan = DailyGrowthRate.objects.get(id=plan_id)
        except DailyGrowthRate.DoesNotExist:
            raise serializers.ValidationError({'detail': 'Selected plan does not exist.'})
        
        amount = float(amount)
        if amount < float(plan.min_amount) or amount > float(plan.max_amount):
            raise serializers.ValidationError({'detail': f'Amount must be between {plan.min_amount} and {plan.max_amount} for this plan.'})
        
        if user.balance < amount:
            raise serializers.ValidationError({'detail': 'Insufficient wallet balance.'})
        
        # Deduct from user balance
        user.balance -= Decimal(str(amount))
        user.save()
        
        # Save the daily growth
        serializer.save(user=user, plan=plan, rate=plan.rate, amount=amount, activated_date=timezone.now())
        
        # Create transaction
        Transaction.objects.create(
            customer=user,
            type='invest',
            amount=amount,
            reference=f"Daily Growth Investment ({plan.name})"
        )

    @action(detail=True, methods=['post'])
    def claim(self, request, pk=None):
        user = request.user
        try:
            growth = DailyGrowth.objects.get(pk=pk, user=user, status='active')
        except DailyGrowth.DoesNotExist:
            return Response({'detail': 'Active daily growth not found.'}, status=404)
        
        # Check if 30 days have passed since investment
        days_since_investment = (timezone.now().date() - growth.activated_date.date()).days
        if days_since_investment < 30:
            remaining_days = 30 - days_since_investment
            return Response({
                'detail': f'You can only claim after 30 days from investment. You have {remaining_days} days remaining.'
            }, status=400)
        
        grown_amount = growth.grown_amount()
        # Credit grown amount to user wallet
        user.balance += Decimal(str(grown_amount))
        user.save()
        # Mark as claimed
        growth.status = 'claimed'
        growth.claimed_date = timezone.now()
        growth.save()
        # Create transaction
        Transaction.objects.create(
            customer=user,
            type='return',
            amount=grown_amount,
            reference=f"Claimed Daily Growth ({growth.plan.name})"
        )
        return Response({
            'message': 'Daily growth claimed successfully.',
            'amount': round(grown_amount, 2),
            'new_balance': float(user.balance)
        })

# --- Withdrawal ViewSet ---
class WithdrawalViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Withdrawal.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        amount = serializer.validated_data['amount']
        
        if user.balance < amount:
            raise serializers.ValidationError({'detail': 'Insufficient wallet balance.'})
        
        # Deduct from user balance
        user.balance -= Decimal(str(amount))
        user.save()
        
        # Create withdrawal record
        withdrawal = serializer.save(user=user)
        
        # Create transaction record
        Transaction.objects.create(
            customer=user,
            type='withdrawal',
            amount=amount,
            reference=f"Withdrawal request - {withdrawal.id}"
        )
        
        return Response({
            'message': 'Withdrawal request submitted successfully.',
            'new_balance': float(user.balance)
        }, status=status.HTTP_201_CREATED)
