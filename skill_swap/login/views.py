from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if email and password:
            with connection.cursor() as c:
                # 1. Explicitly select columns so we know the order (email first, then username)
                c.execute("SELECT email, username FROM users WHERE email=%s AND password=%s", [email, password])
                x = c.fetchone()
            
                if x:
                    # 2. Assign correctly based on the SELECT order above
                    request.session['user_email'] = x[0]  # First column is email
                    request.session['user_name'] = x[1]   # Second column is username
                    
                    # Note: We are not fetching 'user_pic' here because it is in the 'user_profiles' table,
                    # not the 'users' table. The home_view handles fetching the pic later.
                    
                    return redirect('/dashboard/')
                else:
                    messages.error(request, "Wrong Email or Password")
                    return render(request, 'index.html')
            
    return render(request, 'index.html')