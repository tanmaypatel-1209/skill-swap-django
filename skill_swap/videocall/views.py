from django.shortcuts import render, redirect
from django.db.models import Q
from django.db import connection as db_connection
from .models import Connection 

def video_call_dashboard(request):
    my_email = request.session.get('user_email')
    
    if not my_email:
        return redirect('login_view') 

    my_connections = Connection.objects.filter(
        (Q(sender_email=my_email) | Q(receiver_email=my_email)) & 
        Q(status='accepted')
    )

    partners = []
    
    for conn in my_connections:
        if conn.sender_email == my_email:
            partner_email = conn.receiver_email
        else:
            partner_email = conn.sender_email
            
        partner_name = "Unknown"
        partner_pic = ""
        partner_location = "Location Unknown"
        skills_expert = []
        skills_learn = []

        with db_connection.cursor() as c:
            sql = """
                SELECT u.username, p.profile_pic, p.location, p.can_teach, p.want_to_learn
                FROM users u 
                LEFT JOIN user_profiles p ON u.email = p.email 
                WHERE u.email = %s
            """
            c.execute(sql, [partner_email])
            row = c.fetchone()
            
            if row:
                partner_name = row[0]
                partner_pic = row[1]
                partner_location = row[2] if row[2] else "Nadiad, Gujarat"
                
                raw_teach = row[3]
                raw_learn = row[4]
                
                if raw_teach:
                    skills_expert = [s.strip() for s in raw_teach.split(',')][:2]
                if raw_learn:
                    skills_learn = [s.strip() for s in raw_learn.split(',')][:2]
            
        partners.append({
            'email': partner_email,
            'name': partner_name,
            'pic': partner_pic if partner_pic else "", 
            'location': partner_location,
            'skills_expert': skills_expert,
            'skills_learn': skills_learn,
            'room_code': conn.video_call_code 
        })

    return render(request, 'videocall_dashboard.html', {'partners': partners})


from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from .models import Connection

def video_room(request, room_code):
    my_email = request.session.get('user_email')
    if not my_email:
        return redirect('login_view')

    conn = get_object_or_404(Connection, video_call_code=room_code)

    if conn.sender_email == my_email:
        partner_email = conn.receiver_email
    elif conn.receiver_email == my_email:
        partner_email = conn.sender_email
    else:
        return HttpResponseForbidden("You are not authorized to join this call.")

    my_peer_id = my_email.replace('@', '-at-').replace('.', '-dot-')
    remote_peer_id = partner_email.replace('@', '-at-').replace('.', '-dot-')

    context = {
        'room_code': room_code,
        'my_peer_id': my_peer_id,
        'remote_peer_id': remote_peer_id,
        'partner_email': partner_email
    }
    return render(request, 'videocall_room.html', context)