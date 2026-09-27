
import streamlit as st
import sqlite3
from datetime import date, time, datetime, timedelta

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Meeting Manager",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_FILE = "meeting_manager.db"

# ============================================================
# DATABASE
# ============================================================
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT UNIQUE NOT NULL,
            capacity INTEGER NOT NULL,
            facilities TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_name TEXT NOT NULL,
            organizer TEXT NOT NULL,
            participants INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(room_id)
        )
        """
    )

    room_count = cur.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]

    if room_count == 0:
        rooms = [
            ("Room A", 4, "None"),
            ("Room B", 8, "Projector"),
            ("Room C", 12, "Projector, Whiteboard"),
            ("Room D", 20, "Projector, Whiteboard"),
        ]
        cur.executemany(
            "INSERT INTO rooms (room_name, capacity, facilities) VALUES (?, ?, ?)",
            rooms,
        )

    conn.commit()
    conn.close()


init_database()


# ============================================================
# DATABASE HELPERS
# ============================================================
def get_rooms():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM rooms ORDER BY capacity ASC"
    ).fetchall()
    conn.close()
    return rows


def get_room(room_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM rooms WHERE room_id = ?", (room_id,)
    ).fetchone()
    conn.close()
    return row


def get_all_bookings():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            b.*,
            r.room_name,
            r.capacity,
            r.facilities
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        ORDER BY b.booking_date ASC, b.start_time ASC
        """
    ).fetchall()
    conn.close()
    return rows


def get_bookings_for_date(selected_date):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            b.*,
            r.room_name,
            r.capacity,
            r.facilities
        FROM bookings b
        JOIN rooms r ON b.room_id = r.room_id
        WHERE b.booking_date = ?
        ORDER BY b.start_time ASC
        """,
        (selected_date.isoformat(),),
    ).fetchall()
    conn.close()
    return rows


def time_to_minutes(value):
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def is_room_available(room_id, booking_date, start_value, end_value):
    conn = get_connection()
    existing = conn.execute(
        """
        SELECT start_time, end_time
        FROM bookings
        WHERE room_id = ?
          AND booking_date = ?
        """,
        (room_id, booking_date.isoformat()),
    ).fetchall()
    conn.close()

    new_start = time_to_minutes(start_value)
    new_end = time_to_minutes(end_value)

    for booking in existing:
        old_start = time_to_minutes(booking["start_time"])
        old_end = time_to_minutes(booking["end_time"])

        # Overlap exists when:
        # new_start < old_end AND new_end > old_start
        if new_start < old_end and new_end > old_start:
            return False

    return True


def find_suitable_room(
    participants,
    required_facilities,
    booking_date,
    start_value,
    end_value,
):
    rooms = get_rooms()
    suitable = []

    for room in rooms:
        if room["capacity"] < participants:
            continue

        room_facilities = {
            item.strip().lower()
            for item in room["facilities"].split(",")
            if item.strip()
        }

        if required_facilities:
            if not set(f.lower() for f in required_facilities).issubset(
                room_facilities
            ):
                continue

        if not is_room_available(
            room["room_id"],
            booking_date,
            start_value,
            end_value,
        ):
            continue

        suitable.append(room)

    # Smallest room that satisfies all requirements.
    suitable.sort(key=lambda r: (r["capacity"], r["room_id"]))

    return suitable[0] if suitable else None


def create_booking(
    meeting_name,
    organizer,
    participants,
    room_id,
    booking_date,
    start_value,
    end_value,
):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO bookings
        (
            meeting_name,
            organizer,
            participants,
            room_id,
            booking_date,
            start_time,
            end_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            meeting_name,
            organizer,
            participants,
            room_id,
            booking_date.isoformat(),
            start_value,
            end_value,
        ),
    )
    conn.commit()
    conn.close()


def cancel_booking(booking_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM bookings WHERE booking_id = ?",
        (booking_id,),
    )
    conn.commit()
    conn.close()


def load_demo_booking():
    """Add one safe demo booking only when there are no bookings."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

    if count == 0:
        room_a = conn.execute(
            "SELECT room_id FROM rooms WHERE room_name = 'Room A'"
        ).fetchone()

        if room_a:
            conn.execute(
                """
                INSERT INTO bookings
                (
                    meeting_name,
                    organizer,
                    participants,
                    room_id,
                    booking_date,
                    start_time,
                    end_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Presentation",
                    "Anjali",
                    4,
                    room_a["room_id"],
                    date.today().isoformat(),
                    "09:00",
                    "10:00",
                ),
            )
            conn.commit()

    conn.close()


# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🏢 Meeting Manager")
    st.divider()

    st.subheader("Navigation")

    page = st.radio(
        "Go to",
        [
            "🏠 Dashboard",
            "📅 Book a Room",
            "📋 Bookings",
            "🏢 Room Information",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.subheader("Smart Allocation")
    st.write(
        "Automatically assigns the most suitable available room "
        "based on capacity, facilities and schedule."
    )

    st.divider()

    st.caption("Meeting Room Allocation System")
    st.caption("Python • Streamlit • SQLite")


# ============================================================
# DASHBOARD
# ============================================================
if page == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.write("Manage meeting rooms, bookings and schedules from one place.")

    rooms = get_rooms()
    today = date.today()
    today_bookings = get_bookings_for_date(today)

    booked_room_ids = {booking["room_id"] for booking in today_bookings}

    total_rooms = len(rooms)
    booked_rooms = len(booked_room_ids)
    available_rooms = total_rooms - booked_rooms
    total_capacity = sum(room["capacity"] for room in rooms)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("🏢 Total Rooms", total_rooms)
    c2.metric("🟢 Available Rooms", available_rooms)
    c3.metric("🔴 Booked Rooms", booked_rooms)
    c4.metric("👥 Total Capacity", total_capacity)

    st.divider()

    st.subheader("🏢 Meeting Rooms")
    st.caption(f"Room availability for {today.strftime('%d %B %Y')}")

    for row_start in range(0, len(rooms), 2):
        cols = st.columns(2)

        for index, room in enumerate(rooms[row_start:row_start + 2]):
            with cols[index]:
                is_booked = room["room_id"] in booked_room_ids

                with st.container(border=True):
                    st.subheader(f"🏢 {room['room_name']}")
                    st.write(f"👥 Capacity: **{room['capacity']} participants**")
                    st.write(f"🛠️ Facilities: **{room['facilities']}**")

                    if is_booked:
                        st.error("🔴 BOOKED TODAY")
                    else:
                        st.success("🟢 AVAILABLE TODAY")

    st.divider()

    st.subheader("📊 Today's Schedule")

    if not today_bookings:
        st.info("No meetings are scheduled for today.")
    else:
        for booking in today_bookings:
            with st.container(border=True):
                left, middle, right = st.columns([2, 2, 1])

                with left:
                    st.markdown(f"### 📌 {booking['meeting_name']}")
                    st.write(f"Organizer: {booking['organizer']}")

                with middle:
                    st.write(f"🏢 **{booking['room_name']}**")
                    st.write(f"👥 {booking['participants']} participants")

                with right:
                    st.write(f"📅 {booking['booking_date']}")
                    st.write(
                        f"⏰ {booking['start_time']} – {booking['end_time']}"
                    )


# ============================================================
# BOOK A ROOM
# ============================================================
elif page == "📅 Book a Room":
    st.title("📅 Book a Room")
    st.write(
        "Enter the meeting requirements. The system will automatically "
        "select the smallest suitable available room."
    )

    with st.container(border=True):
        st.subheader("Meeting Details")

        meeting_name = st.text_input(
            "Meeting Name",
            placeholder="Example: Project Discussion",
        )

        organizer = st.text_input(
            "Organizer",
            placeholder="Example: Anjali",
        )

        col1, col2 = st.columns(2)

        with col1:
            participants = st.number_input(
                "Number of Participants",
                min_value=1,
                max_value=20,
                value=4,
                step=1,
            )

            booking_date = st.date_input(
                "Meeting Date",
                value=date.today(),
                min_value=date.today(),
            )

        with col2:
            start_time = st.time_input(
                "Start Time",
                value=time(9, 0),
                step=timedelta(minutes=30),
            )

            end_time = st.time_input(
                "End Time",
                value=time(10, 0),
                step=timedelta(minutes=30),
            )

        st.subheader("Required Facilities")

        facility_col1, facility_col2 = st.columns(2)

        with facility_col1:
            projector = st.checkbox("📽️ Projector")

        with facility_col2:
            whiteboard = st.checkbox("📝 Whiteboard")

        required_facilities = []

        if projector:
            required_facilities.append("Projector")

        if whiteboard:
            required_facilities.append("Whiteboard")

        st.divider()

        if st.button(
            "🔎 Find & Allocate Room",
            type="primary",
            use_container_width=True,
        ):
            meeting_name_clean = meeting_name.strip()
            organizer_clean = organizer.strip()

            if not meeting_name_clean:
                st.error("Please enter the meeting name.")
                st.stop()

            if not organizer_clean:
                st.error("Please enter the organizer name.")
                st.stop()

            if end_time <= start_time:
                st.error("End time must be later than start time.")
                st.stop()

            start_value = start_time.strftime("%H:%M")
            end_value = end_time.strftime("%H:%M")

            selected_room = find_suitable_room(
                participants=participants,
                required_facilities=required_facilities,
                booking_date=booking_date,
                start_value=start_value,
                end_value=end_value,
            )

            if selected_room is None:
                st.error(
                    "No suitable room is available for the selected "
                    "date, time, capacity and facilities."
                )
            else:
                create_booking(
                    meeting_name=meeting_name_clean,
                    organizer=organizer_clean,
                    participants=participants,
                    room_id=selected_room["room_id"],
                    booking_date=booking_date,
                    start_value=start_value,
                    end_value=end_value,
                )

                st.success("🎉 YOUR SLOT IS BOOKED!")

                st.info(
                    f"**{selected_room['room_name']}** has been allocated "
                    f"for **{meeting_name_clean}**."
                )

                result1, result2, result3 = st.columns(3)

                result1.metric(
                    "🏢 Allocated Room",
                    selected_room["room_name"],
                )

                result2.metric(
                    "👥 Capacity",
                    f"{selected_room['capacity']}",
                )

                result3.metric(
                    "⏰ Time",
                    f"{start_value} – {end_value}",
                )

                st.caption(
                    f"Date: {booking_date.strftime('%d %B %Y')} • "
                    f"Facilities: {selected_room['facilities']}"
                )


# ============================================================
# BOOKINGS
# ============================================================
elif page == "📋 Bookings":
    st.title("📋 Meeting Schedule")
    st.write("View and manage all scheduled meetings.")

    selected_date = st.date_input(
        "Select Date",
        value=date.today(),
        key="booking_schedule_date",
    )

    bookings = get_bookings_for_date(selected_date)

    st.subheader(
        f"{len(bookings)} scheduled meeting(s)"
    )

    if not bookings:
        st.info(
            f"No meetings are scheduled for "
            f"{selected_date.strftime('%d %B %Y')}."
        )
    else:
        for booking in bookings:
            with st.container(border=True):
                left, middle, right = st.columns([3, 3, 1])

                with left:
                    st.markdown(f"### 📌 {booking['meeting_name']}")
                    st.write(f"Organizer: **{booking['organizer']}**")

                with middle:
                    st.write(f"🏢 Room: **{booking['room_name']}**")
                    st.write(
                        f"👥 Participants: **{booking['participants']}**"
                    )
                    st.write(
                        f"⏰ {booking['start_time']} – {booking['end_time']}"
                    )

                with right:
                    st.write("")
                    if st.button(
                        "Cancel",
                        key=f"cancel_{booking['booking_id']}",
                        type="secondary",
                    ):
                        cancel_booking(booking["booking_id"])
                        st.success("Booking cancelled.")
                        st.rerun()


# ============================================================
# ROOM INFORMATION
# ============================================================
elif page == "🏢 Room Information":
    st.title("🏢 Room Information")
    st.info(
        "View the capacity and facilities available in each meeting room."
    )

    rooms = get_rooms()
    today_bookings = get_bookings_for_date(date.today())
    booked_room_ids = {booking["room_id"] for booking in today_bookings}

    for row_start in range(0, len(rooms), 2):
        cols = st.columns(2)

        for index, room in enumerate(rooms[row_start:row_start + 2]):
            with cols[index]:
                is_booked = room["room_id"] in booked_room_ids

                with st.container(border=True):
                    st.subheader(f"🏢 {room['room_name']}")
                    st.write(
                        f"👥 Capacity: **{room['capacity']} participants**"
                    )
                    st.write(
                        f"🛠️ Facilities: **{room['facilities']}**"
                    )

                    if is_booked:
                        st.error("🔴 Booked today")
                    else:
                        st.success("🟢 Available today")

    st.divider()

    st.subheader("📌 Allocation Logic")
    st.write(
        "1. Check participant capacity."
    )
    st.write(
        "2. Check the requested facilities."
    )
    st.write(
        "3. Check whether the room is free during the requested time."
    )
    st.write(
        "4. Among all suitable rooms, select the smallest room that "
        "satisfies the requirements."
    )

# End of application.
