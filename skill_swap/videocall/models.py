from django.db import models

# Change 'class connection' to 'class Connection'
class Connection(models.Model):
    id = models.AutoField(primary_key=True)
    sender_email = models.CharField(max_length=100)
    receiver_email = models.CharField(max_length=100)
    
    STATUS_CHOICES = (
        ('pending', 'pending'),
        ('accepted', 'accepted'),
        ('rejected', 'rejected'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    video_call_code = models.CharField(max_length=100, unique=True, null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False 
        db_table = 'connections' # This ensures it still links to your existing SQL table

    def __str__(self):
        return f"{self.sender_email} -> {self.receiver_email}"