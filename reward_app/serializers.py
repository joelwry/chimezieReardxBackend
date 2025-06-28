from rest_framework import serializers
from .models import Activity, Payment, SurveyTask,CustomUser, Transaction, Reward
from django.contrib.auth.password_validation import validate_password

class SurveyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SurveyTask
        fields = '__all__'

class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'password', 'balance']
        read_only_fields = ['balance']
    '''
    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
        )
        return user
    '''
    def create(self, validated_data):
        user = CustomUser(
            email=validated_data['email'],
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])  # 🔐 
        user.save()
        return user

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['status', 'created_at']

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = '__all__'
        read_only_fields = ['reward_earned', 'completed_at', 'amount', 'rate', 'start_date', 'return_date', 'is_returned']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta : 
        model = Transaction
        fields = '__all__'
        read_only_fields = ['created_at'] # can still include Customer etc

class DashboardSerializer(serializers.Serializer):
    user_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    tasks_completed = serializers.IntegerField()
    available_tasks = serializers.IntegerField()
    balance_overview = serializers.ListField(child=serializers.DictField())
    available_tasks_list = SurveyTaskSerializer(many=True)
    recent_activity = ActivitySerializer(many=True)

class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = '__all__'
