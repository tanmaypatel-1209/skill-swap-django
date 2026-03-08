from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
import os
import json

ALLOWED_SKILLS = [
    'Chemistry','Chess','Cooking','Fitness Coaching','Mathematics','Physics','Yoga',
    'Accounting','Copywriting','Digital Marketing','Entrepreneurship','Public Speaking','SEO',
    'Animation','Graphic Design','Illustration','Photography','UI/UX Design','Video Editing',
    'English','French','German','Japanese','Mandarin','Spanish',
    'Audio Engineering','Guitar','Music Production','Piano','Singing',
    'AI/Machine Learning','Data Science','JavaScript','Mobile App Dev','Python','Web Development'
]


def home_view(request):

    if 'user_email' not in request.session:
        return redirect('/')

    current_email = request.session.get('user_email')
    query_text = request.GET.get('q', '')

    with connection.cursor() as cursor:

        sql = """
        SELECT u.username,p.location,p.can_teach,p.want_to_learn,p.profile_pic,
               u.email,p.average_rating,p.review_count,c.status,c.sender_email
        FROM users u
        JOIN user_profiles p ON u.email = p.email
        LEFT JOIN connections c ON
            (c.sender_email = %s AND c.receiver_email = u.email) OR
            (c.sender_email = u.email AND c.receiver_email = %s)
        WHERE u.email != %s
        """

        params = [current_email, current_email, current_email]

        if query_text:
            sql += """
            AND (
                u.username LIKE %s OR
                p.can_teach LIKE %s OR
                p.want_to_learn LIKE %s OR
                p.location LIKE %s
            )
            """

            search_param = f"%{query_text}%"
            params.extend([search_param, search_param, search_param, search_param])

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        cursor.execute(
            "SELECT profile_pic FROM user_profiles WHERE email = %s",
            [current_email]
        )
        my_data = cursor.fetchone()
        my_pic = my_data[0] if my_data else None

    users = []

    for row in rows:

        conn_status = row[8]
        conn_sender = row[9]

        ui_status = "Connect"
        is_connected = False

        if conn_status == 'accepted':
            ui_status = "Connected"
            is_connected = True

        elif conn_status == 'pending':
            if conn_sender == current_email:
                ui_status = "Request Sent"
            else:
                ui_status = "Accept Request"

        teaches = [s.strip() for s in row[2].split(',')] if row[2] else []
        learns = [s.strip() for s in row[3].split(',')] if row[3] else []

        users.append({
            'name': row[0],
            'location': row[1],
            'teaches': teaches,
            'learns': learns,
            'pic': row[4],
            'email': row[5],
            'rating': float(row[6]) if row[6] else 0.0,
            'review_count': row[7] if row[7] else 0,
            'connection_status': ui_status,
            'can_review': is_connected
        })

    context = {
        'user_name': request.session.get('user_name'),
        'user_email': current_email,
        'user_pic': my_pic,
        'other_users': users,
        'search_query': query_text
    }

    return render(request, 'home.html', context)


def submit_review_view(request):

    if request.method == 'POST' and 'user_email' in request.session:

        reviewer = request.session.get('user_email')
        reviewee = request.POST.get('reviewee_email')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, "Please select rating")
            return redirect('/dashboard/')

        with connection.cursor() as cursor:

            cursor.execute("""
            SELECT status FROM connections
            WHERE ((sender_email=%s AND receiver_email=%s)
            OR (sender_email=%s AND receiver_email=%s))
            AND status='accepted'
            """, [reviewer, reviewee, reviewee, reviewer])

            if not cursor.fetchone():
                messages.error(request, "You must be connected")
                return redirect('/dashboard/')

            cursor.execute("""
            INSERT INTO reviews (reviewer_email,reviewee_email,rating,comment)
            VALUES (%s,%s,%s,%s)
            """, [reviewer, reviewee, rating, comment])

            cursor.execute("""
            SELECT AVG(rating),COUNT(id)
            FROM reviews
            WHERE reviewee_email=%s
            """, [reviewee])

            avg, count = cursor.fetchone()

            cursor.execute("""
            UPDATE user_profiles
            SET average_rating=%s,review_count=%s
            WHERE email=%s
            """, [avg, count, reviewee])

            messages.success(request, "Review submitted")

    return redirect('/dashboard/')


def profile_edit_view(request):

    if 'user_email' not in request.session:
        return redirect('/')

    email = request.session.get('user_email')
    name = request.session.get('user_name')

    with connection.cursor() as cursor:

        cursor.execute("""
        SELECT location,can_teach,want_to_learn,profile_pic
        FROM user_profiles
        WHERE email=%s
        """, [email])

        data = cursor.fetchone()

        if request.method == 'POST':

            username = request.POST.get('username')
            location = request.POST.get('location')
            teach = request.POST.get('can_teach','')
            learn = request.POST.get('want_to_learn','')

            teach_list = [s.strip() for s in teach.split(',') if s.strip()]
            learn_list = [s.strip() for s in learn.split(',') if s.strip()]

            invalid = [s for s in teach_list+learn_list if s not in ALLOWED_SKILLS]

            if invalid:
                messages.error(request,"Invalid skills")
                return redirect('/profile/edit/')

            profile_pic = request.FILES.get('profile_pic')
            request.session['user_name'] = username

            pic_url = None

            if profile_pic:
                folder = 'media/profile_pics/'
                os.makedirs(folder, exist_ok=True)

                fs = FileSystemStorage(location=folder)
                filename = fs.save(f"{email}_{profile_pic.name}", profile_pic)

                pic_url = f"/{folder}{filename}"

            else:
                pic_url = data[3] if data else None

            cursor.execute(
                "UPDATE users SET username=%s WHERE email=%s",
                [username,email]
            )

            cursor.execute("""
            UPDATE user_profiles
            SET location=%s,can_teach=%s,want_to_learn=%s,profile_pic=COALESCE(%s,profile_pic)
            WHERE email=%s
            """, [location,teach,learn,pic_url,email])

            messages.success(request,"Profile updated")
            return redirect('/dashboard/')

    context = {
        'current_user_name': name,
        'current_location': data[0] if data else '',
        'current_profile_pic': data[3] if data else None
    }

    return render(request,'profile.html',context)


def send_request_view(request):

    if request.method == 'POST' and 'user_email' in request.session:

        data = json.loads(request.body)
        sender = request.session.get('user_email')
        receiver = data.get('receiver_email')

        if not receiver or sender == receiver:
            return JsonResponse({'status':'error'})

        with connection.cursor() as cursor:

            cursor.execute("""
            SELECT id FROM connections
            WHERE (sender_email=%s AND receiver_email=%s)
            """,[sender,receiver])

            if cursor.fetchone():
                return JsonResponse({'status':'error','message':'Already sent'})

            cursor.execute("""
            INSERT INTO connections(sender_email,receiver_email,status)
            VALUES(%s,%s,'pending')
            """,[sender,receiver])

        return JsonResponse({'status':'success'})

    return JsonResponse({'status':'error'})


def send_message_view(request):

    if request.method == 'POST' and 'user_email' in request.session:

        data = json.loads(request.body)

        sender = request.session.get('user_email')
        receiver = data.get('receiver_email')
        message = data.get('message')

        if not message or not receiver:
            return JsonResponse({'status':'error'})

        with connection.cursor() as cursor:

            cursor.execute("""
            SELECT status FROM connections
            WHERE ((sender_email=%s AND receiver_email=%s)
            OR (sender_email=%s AND receiver_email=%s))
            AND status='accepted'
            """,[sender,receiver,receiver,sender])

            if not cursor.fetchone():
                return JsonResponse({'status':'error'})

            cursor.execute("""
            INSERT INTO chat_messages(sender_email,receiver_email,message)
            VALUES(%s,%s,%s)
            """,[sender,receiver,message])

        return JsonResponse({'status':'success'})

    return JsonResponse({'status':'error'})


def get_chat_history(request):

    if 'user_email' not in request.session:
        return JsonResponse({'status':'error'})

    current = request.session.get('user_email')
    other = request.GET.get('user')

    with connection.cursor() as cursor:

        cursor.execute("""
        SELECT sender_email,message,timestamp
        FROM chat_messages
        WHERE (sender_email=%s AND receiver_email=%s)
        OR (sender_email=%s AND receiver_email=%s)
        ORDER BY timestamp
        """,[current,other,other,current])

        rows = cursor.fetchall()

    msgs = []

    for r in rows:
        msgs.append({
            'sender': r[0],
            'text': r[1],
            'time': r[2].strftime("%H:%M")
        })

    return JsonResponse({
        'status':'success',
        'messages':msgs,
        'current_user':current
    })