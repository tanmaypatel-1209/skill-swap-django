from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from django.core.files.storage import FileSystemStorage


def signup_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email', '').lower()
        password = request.POST.get('password')

        if not email.endswith('@gmail.com'):
            messages.error(request, 'Only @gmail.com addresses are allowed!')
            return render(request, 'signup.html')

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", [email])
        user = cursor.fetchone()

        if user:
            messages.error(request, 'Email already registered!')
            return render(request, 'signup.html')

        cursor.execute("INSERT INTO users VALUES(%s,%s,%s)", [email, name, password])
        request.session['new_user_email'] = email
        return redirect('/profile/')

    return render(request, 'signup.html')


ALLOWED_SKILLS = [
    'Chemistry', 'Chess', 'Cooking', 'Fitness Coaching', 'Mathematics', 'Physics', 'Yoga',
    'Accounting', 'Copywriting', 'Digital Marketing', 'Entrepreneurship', 'Public Speaking', 'SEO',
    'Animation', 'Graphic Design', 'Illustration', 'Photography', 'UI/UX Design', 'Video Editing',
    'English', 'French', 'German', 'Japanese', 'Mandarin', 'Spanish',
    'Audio Engineering', 'Guitar', 'Music Production', 'Piano', 'Singing',
    'AI/Machine Learning', 'Data Science', 'JavaScript', 'Mobile App Dev', 'Python', 'Web Development'
]


def complete_profile_view(request):
    email = request.session.get('new_user_email')

    if not email:
        return redirect('/')

    if request.method == 'POST':
        want_learn = request.POST.get('want_learn')
        can_teach = request.POST.get('can_teach')
        location = request.POST.get('location')
        experience = request.POST.get('experience')
        availability = request.POST.get('availability')
        mode = request.POST.get('mode')

        if want_learn not in ALLOWED_SKILLS or can_teach not in ALLOWED_SKILLS:
            messages.error(request, "Please select a valid skill from the dropdown list.")
            return render(request, 'complete_profile.html')

        uploaded_file = request.FILES.get('profile_pic')
        pic_url = None

        if uploaded_file:
            fs = FileSystemStorage()
            file_name = fs.save(uploaded_file.name, uploaded_file)
            pic_url = fs.url(file_name)

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_profiles
                (email, profile_pic, want_to_learn, can_teach, location, experience, availability, mode)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, [email, pic_url, want_learn, can_teach, location, experience, availability, mode])

        del request.session['new_user_email']
        messages.success(request, "Profile Setup Complete! You can now login.")

        return redirect('/')

    return render(request, 'complete_profile.html')