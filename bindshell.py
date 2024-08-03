import os
import socket
import subprocess
import click
from threading import Thread
from colorama import init, Fore, Style


init(autoreset=True)

def run_cmd(cmd, cwd):
    output = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, cwd=cwd)
    return output.stdout, output.stderr

def handle_input(client_socket):
    print(Fore.CYAN + "Started handle_input thread")
    cwd = os.getcwd()  # Keep track of the current working directory
    while True:
        chunks = []
        try:
            chunk = client_socket.recv(2048)
            if not chunk:
                print(Fore.YELLOW + "No data received, closing connection")
                break
            chunks.append(chunk)
            while len(chunk) != 0 and chr(chunk[-1]) != '\n':
                chunk = client_socket.recv(2048)
                if not chunk:
                    print(Fore.YELLOW + "No more data, breaking loop")
                    break
                chunks.append(chunk)
            cmd = (b''.join(chunks)).decode()[:-1]

            if cmd.lower() == 'exit':
                print(Fore.YELLOW + "Client sent exit command, closing connection")
                client_socket.close()
                break

            if cmd.startswith('cd '):
                new_dir = cmd.split(' ', 1)[1]
                try:
                    os.chdir(new_dir)
                    cwd = os.getcwd()
                    client_socket.sendall(b"Directory changed successfully\n")
                    print(Fore.CYAN + f"Changed directory to: {cwd}")
                except FileNotFoundError:
                    client_socket.sendall(b"Directory not found\n")
                except NotADirectoryError:
                    client_socket.sendall(b"Not a directory\n")
                except PermissionError:
                    client_socket.sendall(b"Permission denied\n")

            elif cmd.startswith('writefile '):
                parts = cmd.split(' ', 2)
                filename = parts[1]
                content = parts[2]
                with open(filename, 'w') as f:
                    f.write(content)
                client_socket.sendall(b"File written successfully\n")
                print(Fore.CYAN + f"Written to file: {filename}")

            elif cmd.startswith('appendfile '):
                parts = cmd.split(' ', 2)
                filename = parts[1]
                content = parts[2]
                with open(filename, 'a') as f:
                    f.write(content + "\n")
                client_socket.sendall(b"File appended successfully\n")
                print(Fore.CYAN + f"Appended to file: {filename}")

            elif cmd.startswith('readfile '):
                filename = cmd.split(' ')[1]
                try:
                    with open(filename, 'r') as f:
                        content = f.read()
                    client_socket.sendall(content.encode())
                except FileNotFoundError:
                    client_socket.sendall(b"File not found\n")
                print(Fore.CYAN + f"Read from file: {filename}")

            else:
                print(Fore.CYAN + f"Running command: {cmd}")
                stdout, stderr = run_cmd(cmd, cwd)
                if stdout:
                    print(Fore.GREEN + stdout.decode())
                    client_socket.sendall(stdout)
                if stderr:
                    print(Fore.RED + stderr.decode())
                    client_socket.sendall(stderr)
        except Exception as e:
            print(Fore.RED + f"Error: {e}")
            client_socket.close()
            break

@click.command()
@click.option('--port', '-p', default=4444, help="Port to bind the server to")
def main(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', port))
        s.listen(4)
        print(Fore.CYAN + f"Server listening on port {port}")

        while True:
            print(Fore.CYAN + "Waiting for a connection...")
            client_socket, client_address = s.accept()
            print(Fore.YELLOW + f"Connection established with {client_address}")
            t = Thread(target=handle_input, args=(client_socket,))
            t.start()
    except Exception as e:
        print(Fore.RED + f"Error: {e}")
    finally:
        s.close()

if __name__ == '__main__':
    main()
