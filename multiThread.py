import socket
import threading

# database
rooms = {}
activities = []
reservations = {}

# HTTP response template
response_template = """\
HTTP/1.1 {status_code} {status_message}
Content-Type: text/html

<html>
  <body>
    {message}
  </body>
</html>
"""


def add_room(name):
    # add room to database if it doesn't already exist
    if name not in rooms:
        rooms[name] = [[False for _ in range(9, 18)] for _ in range(7)]
        with open("room.txt", "a") as f:
            f.write(name + "\n")
        return "200 OK", f"Room {name} added."
    return "400 Bad Request", f"Room {name} already exists."


def remove_room(name):
    # remove room from database if it exists
    if name in rooms:
        del rooms[name]
        with open("room.txt", "w") as f:
            for room in rooms:
                f.write(room + "\n")
        return "200 OK", f"Room {name} removed."
    return "404 Not Found", f"Room {name} does not exist."


def reserve_room(name, day, hour, duration):
    # reserve room if it exists and is available
    if name in rooms:
        day = int(day) - 1
        hour = int(hour) - 9
        duration = int(duration) + 1
        for i in range(hour, hour + duration):
            if rooms[name][day][i]:
                return "403 Forbidden", f"Room {name} is not available at this time."
        for i in range(hour, hour + duration):
            rooms[name][day][i] = True
        return "200 OK", f"Room {name} reserved for day {day + 1} at {hour + 9}:00 for {duration - 1} hours."
    return "404 Not Found", f"Room {name} does not exist."


def check_availability(name, day):
    # check availability of room if it exists
    if name in rooms:
        day = int(day) - 1
        hours = []
        for i, is_available in enumerate(rooms[name][day]):
            if not is_available:
                hours.append(str(i + 9))
        if hours:
            return "200 OK", f"Available hours for room {name} on day {day + 1}: {', '.join(hours)}"
        return "200 OK", f"No hours are available for room {name} on day {day + 1}."
    return "404 Not Found", f"Room {name} does not exist."


def room_handle_request(request):
    # parse request and call appropriate function
    request_lines = request.split("\n")
    request_line = request_lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        return "HTTP/1.1 400 Bad Request\n\nInvalid request."
    request_type, request_url, _ = parts
    request_params = {}
    if "?" in request_url:
        for param in request_url.split("?")[1].split("&"):
            key, value = param.split("=")
            request_params[key] = value
    if request_type == "GET":
        if request_url.startswith("/add"):
            status_code, message = add_room(request_params["name"])
        elif request_url.startswith("/remove"):
            status_code, message = remove_room(request_params["name"])
        elif request_url.startswith("/reserve"):
            status_code, message = reserve_room(request_params["name"], request_params["day"], request_params["hour"],
                                                request_params["duration"])
        elif request_url.startswith("/checkavailability"):
            status_code, message = check_availability(request_params["name"], request_params["day"])
        else:
            status_code = "404 Not Found"
            message = "Invalid request."
    else:
        status_code = "405 Method Not Allowed"
        message = "Method not allowed."
    return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1], message=message)


def add_activity(name):
    # add activity to database if it doesn't already exist
    if name not in activities:
        activities.append(name)
        with open("activities.txt", "a") as f:
            f.write(name + "\n")
        return "200 OK", f"Activity {name} added."
    return "400 Bad Request", f"Activity {name} already exists."


def remove_activity(name):
    # remove activity from database if it exists
    if name in activities:
        activities.remove(name)
        with open("activities.txt", "w") as f:
            for activity in activities:
                f.write(activity + "\n")
        return "200 OK", f"Activity {name} removed."
    return "404 Not Found", f"Activity {name} does not exist."


def check_activity(name):
    # check if activity exists in database
    if name in activities:
        return "200 OK", f"Activity {name} exists."
    return "404 Not Found", f"Activity {name} does not exist."


def activity_handle_request(request):
    # parse request and call appropriate function
    request_lines = request.split("\n")
    request_line = request_lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        return "HTTP/1.1 400 Bad Request\n\nInvalid request."
    request_type, request_url, _ = parts
    request_params = {}
    if "?" in request_url:
        for param in request_url.split("?")[1].split("&"):
            key, value = param.split("=")
            request_params[key] = value
    if request_type == "GET":
        if request_url.startswith("/add"):
            status_code, message = add_activity(request_params["name"])
        elif request_url.startswith("/remove"):
            status_code, message = remove_activity(request_params["name"])
        elif request_url.startswith("/check"):
            status_code, message = check_activity(request_params["name"])
        else:
            status_code = "404 Not Found"
            message = "Invalid request."
    else:
        status_code = "405 Method Not Allowed"
        message = "Method not allowed."
    return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],
                                    message=message)


def reservation_room(room_name, activity_name, day, hour, duration):
    # contact the Activity Server to check if the activity exists
    activity_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    activity_server_sock.connect(("localhost", 8082))
    activity_server_request = f"GET /check?name={activity_name}\n"
    activity_server_sock.send(activity_server_request.encode())
    activity_server_response = activity_server_sock.recv(1024).decode()
    if "404 Not Found" in activity_server_response:
        return "404 Not Found", "Activity does not exist."

    # contact the Room Server to reserve the room
    room_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    room_server_sock.connect(("localhost", 8081))
    room_server_request = f"GET /reserve?name={room_name}&day={day}&hour={hour}&duration={duration}\n"
    room_server_sock.send(room_server_request.encode())
    room_server_response = room_server_sock.recv(1024).decode()
    if "403 Forbidden" in room_server_response:
        return "403 Forbidden", "Room is not available."

    # if the room was successfully reserved, generate a reservation ID and store the reservation
    reservation_id = len(reservations) + 1
    reservations[reservation_id] = (room_name, activity_name, day, hour, duration)
    return "200 OK", f"Room reserved. Reservation ID: {reservation_id}"


def list_availability(room_name, day=None):
    # contact the Room Server to get the availability of the room
    room_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    room_server_sock.connect(("localhost", 8081))
    if day is not None:
        room_server_request = f"GET /checkavailability?name={room_name}&day={day}\n"
    else:
        room_server_request = f"GET /checkavailability?name={room_name}\n"
    room_server_sock.send(room_server_request.encode())
    room_server_response = room_server_sock.recv(1024).decode()
    if "404 Not Found" in room_server_response:
        return "404 Not Found", "Room does not exist."
    if "400 Bad Request" in room_server_response:
        return "400 Bad Request", "Invalid input."
    return "200 OK", room_server_response


def display(reservation_id):
    if reservation_id not in reservations:
        return "404 Not Found", "Reservation does not exist."
    room_name, activity_name, day, hour, duration = reservations[reservation_id]
    return "200 OK", f"Reservation details:<br>Room name: {room_name}<br>Activity name: {activity_name}<br>Day: {day}<br>Hour: {hour}<br>Duration: {duration}"


def reservation_handle_request(request):
    request_lines = request.split("\n")
    request_line = request_lines[0]
    parts = request_line.split(" ")
    if len(parts) != 3:
        return "HTTP/1.1 400 Bad Request\n\nInvalid request."
    request_type, request_url, _ = parts
    request_params = {}
    if "?" in request_url:
        for param in request_url.split("?")[1].split("&"):
            key, value = param.split("=")
            request_params[key] = value
    if request_type == "GET":
        if request_url.startswith("/reserve"):
            status_code, message = reservation_room(request_params["room"], request_params["activity"],
                                                    request_params["day"], request_params["hour"],
                                                    request_params["duration"])
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],
                                            message=message)
        elif request_url.startswith("/listavailability"):
            if "room" not in request_params:
                return "HTTP/1.1 400 Bad Request\n\nInvalid request. Missing 'room' parameter."
            day = request_params.get("day")
            status_code, message = list_availability(request_params["room"], day)
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],
                                            message=message)
        elif request_url.startswith("/display"):
            if "id" not in request_params:
                return "HTTP/1.1 400 Bad Request\n\nInvalid request. Missing 'id' parameter."
            reservation_id = int(request_params["id"])
            status_code, message = display(reservation_id)
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],
                                            message=message)
    return "HTTP/1.1 400 Bad Request\n\nInvalid request."


def room_main():
    port = 8081
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", port))
    sock.listen()
    print(f"Listening on port {port}...\n")
    while True:
        # accept incoming connection and receive request
        connection, _ = sock.accept()
        request = connection.recv(1024).decode()
        print(request)
        # handle request and send response
        response = room_handle_request(request)
        connection.sendall(response.encode())
        # close connection
        connection.close()


def activity_main():
    port = 8082
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", port))
    sock.listen()
    print(f"Listening on port {port}...\n")
    while True:
        conn, addr = sock.accept()
        request = conn.recv(1024).decode()
        print(request)
        response = activity_handle_request(request)
        conn.sendall(response.encode())
        conn.close()


def reservation_main():
    port = 8080
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", port))
    sock.listen()
    print(f"Listening on port {port}...\n")
    while True:
        connect, address = sock.accept()
        request = connect.recv(1024).decode()
        print(f"Received request:\n{request}")
        response = reservation_handle_request(request)
        connect.sendall(response.encode())
        connect.close()


def main():
    # Create three threads
    thread1 = threading.Thread(target=reservation_main)
    thread2 = threading.Thread(target=room_main)
    thread3 = threading.Thread(target=activity_main)

    # Start the threads
    thread1.start()
    thread2.start()
    thread3.start()

    # Wait for the threads to complete
    thread1.join()
    thread2.join()
    thread3.join()


if __name__ == "__main__":
    main()
