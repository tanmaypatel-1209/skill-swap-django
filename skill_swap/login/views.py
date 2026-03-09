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
               
                c.execute("SELECT email, username FROM users WHERE email=%s AND password=%s", [email, password])
                x = c.fetchone()
                if x:
                    request.session['user_email'] = x[0]  
                    request.session['user_name'] = x[1]   
                    return redirect('/dashboard/')
                else:
                    messages.error(request, "Wrong Email or Password")
                    return render(request, 'index.html')
            
    return render(request, 'index.html')