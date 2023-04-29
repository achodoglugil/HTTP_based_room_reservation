import socket

# database of rooms and their availability
import sys

rooms = {}

# HTTP response template
response_template = """\
HTTP/1.1 200 OK
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
        return True
    return False


def remove_room(name):
    # remove room from database if it exists
    if name in rooms:
        del rooms[name]
        return True
    return False


def reserve_room(name, day, hour, duration):
    # reserve room if it exists and is available
    if name in rooms:
        day = int(day) - 1
        hour = int(hour) - 9
        duration = int(duration)
        for i in range(hour, hour + duration):
            if rooms[name][day][i]:
                return False
        for i in range(hour, hour + duration):
            rooms[name][day][i] = True
        return True
    return False


def check_availability(name, day):
    # check availability of room if it exists
    if name in rooms:
        day = int(day) - 1
        hours = []
        for i, is_available in enumerate(rooms[name][day]):
            if not is_available:
                hours.append(str(i + 9))
        return hours
    return None


def handle_request(request):
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
            success = add_room(request_params["name"])
            if success:
                message = f"Room {request_params['name']} added."
            else:
                message = f"Room {request_params['name']} already exists."
            return response_template.format(message=message)
        elif request_url.startswith("/remove"):
            success = remove_room(request_params["name"])
            if success:
                message = f"Room {request_params['name']} removed."
            else:
                message = f"Room {request_params['name']} does not exist."
            return response_template.format(message=message)
        elif request_url.startswith("/reserve"):
            success = reserve_room(request_params["name"], request_params["day"], request_params["hour"],
                                   request_params["duration"])
            if success:
                message = f"Room {request_params['name']} reserved for day {request_params['day']} at {request_params['hour']}:00 for {request_params['duration']} hours."
            else:
                message = f"Could not reserve room {request_params['name']}."
            return response_template.format(message=message)
        elif request_url.startswith("/checkavailability"):
            availability = check_availability(request_params["name"], request_params["day"])
            if availability is not None:
                message = f"Available hours for room {request_params['name']} on day {request_params['day']}: {', '.join(availability)}"
            else:
                message = f"Room {request_params['name']} does not exist."
            return response_template.format(message=message)
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
        # accept incoming connection and receive request
        connection, _ = sock.accept()
        request = connection.recv(1024).decode()
        print(request)
        # handle request and send response
        response = handle_request(request)
        connection.sendall(response.encode())

        # close connection
        connection.close()


if __name__ == "__main__":
    main()
