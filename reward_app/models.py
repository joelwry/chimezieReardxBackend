# users/models.py
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0.00))
    email = models.EmailField(unique=True)
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username

# we should allow this to be able to generate a default/pending tx_hash at first when not supplied .. at the pending state so we can use it to track that person payment ...
class Payment(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('failed', 'Failed')]

    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tx_hash = models.CharField(max_length=256, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} - {self.amount}"

class SurveyTask(models.Model):
    TASK_TYPES = [
        ('survey', 'Survey'),
        ('video', 'Watch Video'),
        ('link', 'Share Link'),
         ('lock', 'Lock Amount'),      # User locks money from wallet
    ('invest', 'Invest Amount'),  # User invests money from wallet  
    ('deposit', 'Deposit & Hold') # User deposits external funds
    ]

    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TASK_TYPES)
    description = models.TextField(blank=True)
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2)
    video_url = models.URLField(blank=True)
    link_to_share = models.URLField(blank=True)
    deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.title

class Activity(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task = models.ForeignKey(SurveyTask, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    reward_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0.00))
    completed_at = models.DateTimeField(null=True, blank=True)
    # New fields for ROI payout
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    return_date = models.DateTimeField(null=True, blank=True)
    is_returned = models.BooleanField(default=False)

    class Meta:
        unique_together = ('customer', 'task')

    def __str__(self):
        base = f"{self.customer.username} - {self.task.title}"
        if self.amount:
            base += f" | Amount: {self.amount}"
        if self.rate:
            base += f" | Rate: {self.rate}%"
        if self.return_date:
            base += f" | Return: {self.return_date}"
        return base

class Transaction(models.Model):
    # In Transaction model - add these types
    TRANSACTION_TYPES = [
        ('earning', 'Earning'), 
        ('withdrawal', 'Withdrawal'), 
        ('funding', 'Funding'),
        ('lock', 'Lock'),           # NEW: When user locks money
        ('unlock', 'Unlock'),       # NEW: When lock period ends
        ('invest', 'Invest'),       # NEW: When user invests
        ('return', 'Return'),       # NEW: When investment returns
        ('reward_claim', 'Reward Claim')  # NEW: When user transfers reward to balance
    ]

    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} - {self.type} - {self.amount}"

class Reward(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='reward')
    total_reward = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal(0.00))

    def __str__(self):
        return f"{self.user.username} - Reward: {self.total_reward}"

# --- Daily Growth Investment Models ---
class DailyGrowthRate(models.Model):
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Daily growth rate as a percentage (e.g. 1.00 for 1%)")

    def __str__(self):
        return f"{self.name} ({self.rate}% per day)"

class DailyGrowth(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("claimed", "Claimed"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="daily_growths")
    rate = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    activated_date = models.DateTimeField()
    claimed_date = models.DateTimeField(null=True, blank=True)
    plan = models.ForeignKey(DailyGrowthRate, on_delete=models.PROTECT, related_name="growths")

    def __str__(self):
        return f"{self.user.username} - {self.amount} @ {self.rate}% - {self.status}"

    def days_active(self):
        from django.utils import timezone
        end_date = self.claimed_date if self.status == "claimed" and self.claimed_date else timezone.now()
        return (end_date.date() - self.activated_date.date()).days

    def grown_amount(self):
        # Compound daily growth
        days = self.days_active()
        return float(self.amount) * ((1 + float(self.rate) / 100) ** days)

# --- Withdrawal Model ---
class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="withdrawals")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - ₦{self.amount} - {self.status}"

