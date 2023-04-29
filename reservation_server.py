import socket
import sys

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

# dictionary to store reservations
reservations = {}


def reserve_room(room_name, activity_name, day, hour, duration):
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


def handle_request(request):
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
            status_code, message = reserve_room(request_params["room"], request_params["activity"],
                                                request_params["day"], request_params["hour"],
                                                request_params["duration"])
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],message=message)
        elif request_url.startswith("/listavailability"):
            if "day" in request_params:
                status_code, message = list_availability(request_params["room"], request_params["day"])
            else:
                status_code, message = list_availability(request_params["room"])
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],message=message)
        elif request_url.startswith("/display"):
            status_code, message = display(int(request_params["id"]))
            return response_template.format(status_code=status_code, status_message=status_code.split(" ")[1],message=message)

    return "HTTP/1.1 400 Bad Request\n\nInvalid request."


def main():
    if len(sys.argv) < 2:
        print("Please specify a port number as an argument.")
        return
    port = int(sys.argv[1])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", port))
    sock.listen()
    print(f"Listening on port {port}...")
    while True:
        connection, _ = sock.accept()
        request = connection.recv(1024).decode()
        print(f"Received request:\n{request}")
        response = handle_request(request)
        connection.send(response.encode())
        connection.close()


if __name__ == "__main__":
    main()
