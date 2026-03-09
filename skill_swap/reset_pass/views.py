import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.db import connection

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", [email])
            user = cursor.fetchone()
        
        if user:
            otp = random.randint(1000, 9999)
            
            try:
                send_mail(
                    'Skill Swap Password Reset',
                    f'Your OTP is: {otp}',
                    settings.EMAIL_HOST_USER,
                    [email]
                )
                
                response = redirect('verify_otp')
                
              
                response.set_signed_cookie('reset_otp', otp, salt='otp_flow', max_age=300)
                response.set_signed_cookie('reset_email', email, salt='otp_flow', max_age=300)
                
                messages.success(request, 'OTP sent successfully!')
                return response
                
            except Exception as e:
                print(e)
                messages.error(request, "Failed to send email.")
        else:
            messages.error(request, "Email not found!")

    return render(request, 'forgot_password.html')

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        
        try:
            real_otp = request.get_signed_cookie('reset_otp', salt='otp_flow')
            
            if int(entered_otp) == int(real_otp):
                return redirect('reset_password')
            else:
                messages.error(request, "Wrong OTP.")
        except:
            messages.error(request, "OTP Expired or Invalid. Try again.")
            return redirect('forgot_password')

    return render(request, 'verify_otp.html')
def reset_password(request):
    if request.method == 'POST':
        new_pass = request.POST.get('new_password')
        
        if len(new_pass) < 8 or len(new_pass) > 15:
            messages.error(request, "Password must be 8-15 characters long.")
            return render(request, 'reset_password.html')

        try:
            email = request.get_signed_cookie('reset_email', salt='otp_flow')
            
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET password = %s WHERE email = %s", [new_pass, email])
            
            response = redirect('/auth/success/') 
            response.delete_cookie('reset_otp')
            response.delete_cookie('reset_email')
            
            messages.success(request, "Password updated! Please login.")
            return response
            
        except Exception as e:
            print("Error:", e)
            if 'cookie' in str(e).lower():
                 messages.error(request, "Session expired. Start over.")
                 return redirect('forgot_password')
            else:
                 
                 return render(request, '/auth/success/')

    return render(request, 'reset_password.html')
def password_success(request):
    return render(request, 'password_success.html')