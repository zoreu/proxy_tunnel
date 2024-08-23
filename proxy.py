import socket
import threading
import select

def handle_client(client_socket, client_address):
    try:
        request = client_socket.recv(4096)
        
        if not request:
            client_socket.close()
            return
        
        first_line = request.decode().split('\n')[0]
        
        if not first_line.strip():
            client_socket.close()
            return
        
        method, path, version = first_line.split()

        # Verificação de requisição para a mensagem de boas-vindas
        if method == "GET" and path == "/":
            welcome_message = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "Connection: close\r\n\r\n"
                "<html><body><h1>Bem-vindo ao Proxy!</h1><p>Este é o servidor proxy em execução.</p></body></html>"
            )
            client_socket.sendall(welcome_message.encode())
            client_socket.close()
            return

        # Verificação da requisição CONNECT
        if method == "CONNECT":
            host, port = path.split(':')
            port = int(port)
            
            try:
                server_socket = socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET, socket.SOCK_STREAM)
                server_socket.connect((host, port))
                
                client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                
                threading.Thread(target=forward, args=(client_socket, server_socket)).start()
                threading.Thread(target=forward, args=(server_socket, client_socket)).start()
            except socket.error as e:
                print(f"Erro ao conectar com {host}: {e}")
                client_socket.close()
        else:
            host = None
            for line in request.decode().split('\r\n'):
                if line.startswith("Host:"):
                    host = line.split(" ")[1]
                    break
            
            if not host:
                client_socket.close()
                return
            
            try:
                server_socket = socket.socket(socket.AF_INET6 if ':' in host else socket.AF_INET, socket.SOCK_STREAM)
                server_socket.connect((host, 80))
                server_socket.sendall(request)
                forward(server_socket, client_socket)
            except socket.error as e:
                print(f"Erro ao conectar com {host}: {e}")
            finally:
                client_socket.close()

    except ValueError as e:
        print(f"Erro ao processar a requisição: {e}")
        client_socket.close()
    except socket.error as e:
        print(f"Erro de socket: {e}")
        client_socket.close()

def forward(source, destination):
    try:
        while True:
            try:
                data = source.recv(4096)
                if len(data) == 0:
                    break
                destination.sendall(data)
            except socket.error as e:
                print(f"Erro ao receber/enviar dados: {e}")
                break
    finally:
        source.close()
        destination.close()

def start_proxy():
    # IPv6 server
    server_ipv6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_ipv6.bind(('::', 8100))
    server_ipv6.listen(5)
    print("Proxy Server running on [::]:8100...")

    # IPv4 server
    server_ipv4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ipv4.bind(('0.0.0.0', 8100))
    server_ipv4.listen(5)
    print("Proxy Server also running on 0.0.0.0:8100...")

    inputs = [server_ipv6, server_ipv4]

    while True:
        readable, _, _ = select.select(inputs, [], [])
        
        for s in readable:
            if s == server_ipv6:
                client_socket, client_address = server_ipv6.accept()
                client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_handler.start()
            elif s == server_ipv4:
                client_socket, client_address = server_ipv4.accept()
                client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
                client_handler.start()

if __name__ == "__main__":
    start_proxy()
