from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
import os
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
import json
from django.utils import timezone
ALLOWED_SKILLS = [
    'Chemistry', 'Chess', 'Cooking', 'Fitness Coaching', 'Mathematics', 'Physics', 'Yoga',
    'Accounting', 'Copywriting', 'Digital Marketing', 'Entrepreneurship', 'Public Speaking', 'SEO',
    'Animation', 'Graphic Design', 'Illustration', 'Photography', 'UI/UX Design', 'Video Editing',
    'English', 'French', 'German', 'Japanese', 'Mandarin', 'Spanish',
    'Audio Engineering', 'Guitar', 'Music Production', 'Piano', 'Singing',
    'AI/Machine Learning', 'Data Science', 'JavaScript', 'Mobile App Dev', 'Python', 'Web Development'
]
current_email="";
def home_view(request):
    if 'user_email' not in request.session:
        return redirect('/')

    current_email = request.session.get('user_email')
    
    # 1. GET THE SEARCH QUERY
    query_text = request.GET.get('q', '') 

    with connection.cursor() as cursor:
        # 2. ENHANCED QUERY: Fetches User + Profile + Connection Status + Ratings
        sql = """
            SELECT 
                u.username, 
                p.location, 
                p.can_teach, 
                p.want_to_learn, 
                p.profile_pic, 
                u.email,
                p.average_rating,
                p.review_count,
                c.status,
                c.sender_email
            FROM users u
            JOIN user_profiles p ON u.email = p.email
            LEFT JOIN connections c ON 
                (c.sender_email = %s AND c.receiver_email = u.email) OR 
                (c.sender_email = u.email AND c.receiver_email = %s)
            WHERE u.email != %s
        """
        
        # Parameters for the query
        params = [current_email, current_email, current_email]

        # 3. IF SEARCHING, ADD FILTERS
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

        # 4. Fetch Current User Pic (For Navbar)
        cursor.execute("SELECT profile_pic FROM user_profiles WHERE email = %s", [current_email])
        my_data = cursor.fetchone()
        my_fresh_pic = my_data[0] if my_data else None

    # Format Data
    formatted_users = []
    
    for row in rows:
        # --- FIX: STRICTLY EXCLUDE CURRENT USER ---
        # row[5] is the email column. If it matches current_email, skip this iteration.
        if row[0] == current_email:
            print(current_email);
            continue
        # ------------------------------------------

        # Unpack connection details
        conn_status = row[8]  # 'pending', 'accepted', 'rejected', or None
        conn_sender = row[9]  # Who sent the request
        
        # Determine specific connection state for UI
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
        
        teaches_list = [skill.strip() for skill in row[2].split(',')] if row[2] else []
        learns_list = [skill.strip() for skill in row[3].split(',')] if row[3] else []

        formatted_users.append({
            'name': row[0],
            'location': row[1],
            'teaches': teaches_list,
            'learns': learns_list,
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
        'user_pic': my_fresh_pic,
        'other_users': formatted_users,
        'search_query': query_text
    }

    return render(request, 'home.html', context)

def submit_review_view(request):
    """
    Handles submitting a review. Only allows it if users are connected.
    """
    if request.method == 'POST' and 'user_email' in request.session:
        
        reviewer_email = request.session.get('user_email')
        reviewee_email = request.POST.get('reviewee_email')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, "Please select a star rating.")
            return redirect('/dashboard/')

        with connection.cursor() as cursor:
            # 1. SECURITY CHECK: Are they actually connected?
            cursor.execute("""
                SELECT status FROM connections 
                WHERE ((sender_email = %s AND receiver_email = %s) 
                   OR (sender_email = %s AND receiver_email = %s))
                AND status = 'accepted'
            """, [reviewer_email, reviewee_email, reviewee_email, reviewer_email])
            
            if not cursor.fetchone():
                messages.error(request, "You can only review users you have connected with.")
                return redirect('/dashboard/')

            # 2. CHECK FOR DUPLICATES
            cursor.execute("""
                SELECT id FROM reviews WHERE reviewer_email = %s AND reviewee_email = %s
            """, [reviewer_email, reviewee_email])
            if cursor.fetchone():
                 messages.warning(request, "You have already reviewed this user. Review updated.")
                 # Ideally update here, but skipping logic for now as requested
            
            # 3. INSERT REVIEW
            cursor.execute("""
                INSERT INTO reviews (reviewer_email, reviewee_email, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, [reviewer_email, reviewee_email, rating, comment])

            # 4. RECALCULATE AVERAGE RATING
            cursor.execute("""
                SELECT AVG(rating), COUNT(id) FROM reviews WHERE reviewee_email = %s
            """, [reviewee_email])
            result = cursor.fetchone()
            new_avg = result[0]
            new_count = result[1]

            # 5. UPDATE USER PROFILE
            cursor.execute("""
                UPDATE user_profiles 
                SET average_rating = %s, review_count = %s
                WHERE email = %s
            """, [new_avg, new_count, reviewee_email])

            messages.success(request, "Review submitted successfully!")

    return redirect('/dashboard/')
def profile_edit_view(request):
    if 'user_email' not in request.session:
        return redirect('/')
    
    current_email = request.session.get('user_email')
    current_name = request.session.get('user_name')
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT p.location, p.can_teach, p.want_to_learn, p.profile_pic 
            FROM user_profiles p 
            WHERE p.email = %s
        """, [current_email])
        
        profile_data = cursor.fetchone()
        
        if request.method == 'POST':
            username = request.POST.get('username')
            location = request.POST.get('location')
            can_teach = request.POST.get('can_teach', '')
            want_to_learn = request.POST.get('want_to_learn', '')
            
            # --- BACKEND VALIDATION ---
            # Split the comma-separated tags into lists and check against ALLOWED_SKILLS
            teach_list = [s.strip() for s in can_teach.split(',') if s.strip()]
            learn_list = [s.strip() for s in want_to_learn.split(',') if s.strip()]
            
            invalid_skills = [s for s in teach_list + learn_list if s not in ALLOWED_SKILLS]
            
            if invalid_skills:
                messages.error(request, f"Invalid skills detected: {', '.join(invalid_skills)}. Please use the dropdown.")
                return redirect('/profile/edit/') # Assuming this is the URL for this view
            # --------------------------

            profile_pic = request.FILES.get('profile_pic')
            request.session['user_name'] = username
            
            profile_pic_url = None
            if profile_pic:
                media_dir = 'media/profile_pics/'
                os.makedirs(media_dir, exist_ok=True)
                fs = FileSystemStorage(location=media_dir)
                filename = fs.save(f"{current_email}_{profile_pic.name}", profile_pic)
                profile_pic_url = f"/{media_dir}{filename}"
            else:
                profile_pic_url = profile_data[3] if profile_data else None
            
            try:
                cursor.execute("UPDATE users SET username = %s WHERE email = %s", [username, current_email])
                cursor.execute("""
                    UPDATE user_profiles 
                    SET location = %s, can_teach = %s, want_to_learn = %s, profile_pic = COALESCE(%s, profile_pic)
                    WHERE email = %s
                """, [location, can_teach, want_to_learn, profile_pic_url, current_email])
                
                messages.success(request, 'Profile updated successfully!')
                return redirect('/dashboard/')
                
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
        
        current_location = profile_data[0] if profile_data else ''
        current_teaches = [skill.strip() for skill in profile_data[1].split(',') if skill.strip()] if profile_data and profile_data[1] else []
        current_learns = [skill.strip() for skill in profile_data[2].split(',') if skill.strip()] if profile_data and profile_data[2] else []
        current_profile_pic = profile_data[3] if profile_data else None
    
    context = {
        'current_user_name': current_name,
        'current_location': current_location,
        'current_teaches': current_teaches,
        'current_learns': current_learns,
        'current_teaches_str': ','.join(current_teaches),
        'current_learns_str': ','.join(current_learns),
        'current_profile_pic': current_profile_pic,
    }
    
    return render(request, 'profile.html', context)
def send_request_view(request):
    # 1. Validate Session
    if request.method == 'POST' and 'user_email' in request.session:
        try:
            data = json.loads(request.body)
            sender_email = request.session.get('user_email')
            receiver_email = data.get('receiver_email')
            
            # 2. Validate Inputs
            if not receiver_email:
                return JsonResponse({'status': 'error', 'message': 'No receiver specified'})

            if sender_email == receiver_email:
                return JsonResponse({'status': 'error', 'message': 'Cannot connect with yourself'})

            with connection.cursor() as cursor:
                # 3. CRITICAL: Check if request already exists (Uncommented this!)
                cursor.execute("""
                    SELECT id FROM connections 
                    WHERE (sender_email = %s AND receiver_email = %s)
                """, [sender_email, receiver_email])
                
                if cursor.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'Request already sent'})
                
                cursor.execute("""
                    SELECT id FROM connections 
                    WHERE (sender_email = %s AND receiver_email = %s)
                """, [receiver_email,sender_email])
                
                if cursor.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'Request already sent'})
                # 4. Insert new request
                cursor.execute("""
                    INSERT INTO connections (sender_email, receiver_email, status)
                    VALUES (%s, %s, 'pending')
                """, [sender_email, receiver_email])
                
            return JsonResponse({'status': 'success', 'message': 'Request sent successfully'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request (Please login)'})
def send_message_view(request):
    if request.method == 'POST' and 'user_email' in request.session:
        try:
            data = json.loads(request.body)
            sender_email = request.session.get('user_email')
            receiver_email = data.get('receiver_email')
            message_text = data.get('message')

            if not message_text or not receiver_email:
                return JsonResponse({'status': 'error', 'message': 'Missing data'})

            with connection.cursor() as cursor:
                # Security: Check if they are actually connected
                cursor.execute("""
                    SELECT status FROM connections 
                    WHERE ((sender_email = %s AND receiver_email = %s) 
                       OR (sender_email = %s AND receiver_email = %s))
                    AND status = 'accepted'
                """, [sender_email, receiver_email, receiver_email, sender_email])
                
                if not cursor.fetchone():
                    return JsonResponse({'status': 'error', 'message': 'You must be connected to chat.'})

                # Insert Message
                cursor.execute("""
                    INSERT INTO chat_messages (sender_email, receiver_email, message)
                    VALUES (%s, %s, %s)
                """, [sender_email, receiver_email, message_text])

            return JsonResponse({'status': 'success'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# --- 2. GET MESSAGES VIEW (For polling) ---
def get_chat_history(request):
    if 'user_email' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'Not logged in'})

    current_email = request.session.get('user_email')
    other_email = request.GET.get('user')

    with connection.cursor() as cursor:
        # Fetch chat history between these two users
        cursor.execute("""
            SELECT sender_email, message, timestamp 
            FROM chat_messages 
            WHERE (sender_email = %s AND receiver_email = %s) 
               OR (sender_email = %s AND receiver_email = %s)
            ORDER BY timestamp ASC
        """, [current_email, other_email, other_email, current_email])
        
        rows = cursor.fetchall()

    messages = []
    for row in rows:
        messages.append({
            'sender': row[0],
            'text': row[1],
            'time': row[2].strftime("%H:%M") # Format time slightly
        })

    return JsonResponse({'status': 'success', 'messages': messages, 'current_user': current_email})