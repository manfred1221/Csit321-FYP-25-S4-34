#!/usr/bin/env python3
"""
Script to update Guest users to Internal Staff role
"""

try:
    import psycopg2
    from config import Config

    print("Connecting to database...")
    conn = psycopg2.connect(**Config.DATABASE_CONFIG)
    cursor = conn.cursor()

    # First, check if there are any Guest users
    cursor.execute("""
        SELECT u.user_id, u.username, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE r.role_name = 'Guest'
    """)
    guest_users = cursor.fetchall()

    if guest_users:
        print(f'\nFound {len(guest_users)} Guest user(s):')
        for user in guest_users:
            print(f'  - User ID: {user[0]}, Username: {user[1]}, Role: {user[2]}')

        # Get the Internal_Staff role_id
        cursor.execute("""
            SELECT role_id FROM roles WHERE role_name IN ('Internal_Staff', 'Internal Staff', 'Staff')
            LIMIT 1
        """)
        staff_role = cursor.fetchone()

        if staff_role:
            staff_role_id = staff_role[0]
            print(f'\nInternal Staff role_id: {staff_role_id}')

            # Update Guest users to Internal Staff
            cursor.execute("""
                UPDATE users
                SET role_id = %s
                WHERE role_id IN (SELECT role_id FROM roles WHERE role_name = 'Guest')
            """, (staff_role_id,))

            conn.commit()
            print(f'\n✓ Successfully updated {cursor.rowcount} Guest user(s) to Internal Staff')
            print('\nYou can now restart your Flask app and staff_john1 will be able to log in!')
        else:
            print('\nError: Internal Staff role not found in database')
            print('Available roles:')
            cursor.execute("SELECT role_id, role_name FROM roles")
            for role in cursor.fetchall():
                print(f'  - ID: {role[0]}, Name: {role[1]}')
    else:
        print('No Guest users found in database')

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
