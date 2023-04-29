import socket

# database of activities
import sys

activities = []

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


def add_activity(name):
    # add activity to database if it doesn't already exist
    if name not in activities:
        activities.append(name)
        with open("activities.txt", "a") as f:
            f.write(name + "\n")
        return True
    return False


def remove_activity(name):
    # remove activity from database if it exists
    if name in activities:
        activities.remove(name)
        with open("activities.txt", "w") as f:
            for activity in activities:
                f.write(activity + "\n")
        return True
    return False


def check_activity(name):
    # check if activity exists in database
    return name in activities


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
            success = add_activity(request_params["name"])
            if success:
                message = f"Activity {request_params['name']} added."
            else:
                message = f"Activity {request_params['name']} already exists."
            return response_template.format(message=message)
        elif request_url.startswith("/remove"):
            success = remove_activity(request_params["name"])
            if success:
                message = f"Activity {request_params['name']} removed."
            else:
                message = f"Activity {request_params['name']} does not exist."
            return response_template.format(message=message)
        elif request_url.startswith("/check"):
            exists = check_activity(request_params["name"])
            if exists:
                message = f"Activity {request_params['name']} exists."
                return response_template.format(message=message)
            else:
                return "HTTP/1.1 404 Not Found\n\nActivity does not exist."
    return "HTTP/1.1 400 Bad Request\n\nInvalid request."


def main():
    if len(sys.argv) < 2:
        print("Please specify a port number as an argument.")
        return
    port = int(sys.argv[1])
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", port))
    sock.listen(1)
    print(f"Listening on port {port}...")
    while True:
        conn, addr = sock.accept()
        request = conn.recv(1024).decode("utf-8")
        print(request)
        response = handle_request(request)
        conn.sendall(response.encode("utf-8"))
        conn.close()


if __name__ == "__main__":
    main()
