import json

# Maximum safe UDP packet size (to avoid fragmentation)
MAX_PACKET_SIZE = 1200


class PacketManager:

    def __init__(self):
        # sequence numbers per client (address → seq)
        self.send_sequence = {}

        # last received sequence per client
        self.last_received = {}

    def send_packet(self, sock, address, data, message_type):
        """
        Create and send a UDP packet with sequence number and type
        """

        # get sequence number for this address
        seq = self.send_sequence.get(address, 0)

        packet = {
            "seq": seq,
            "type": message_type,
            "data": data
        }

        # encode packet
        encoded = json.dumps(packet).encode("utf-8")

        if len(encoded) > MAX_PACKET_SIZE:
            raise ValueError("Packet too large")
        
        sock.sendto(encoded, address)

        # increment sequence number for this client

        self.send_sequence[address] = seq + 1

        sock.recvfrom(4096)

        
    def receive_packet(self, sock):
        """
        Non-blocking receive, validate packet,
        detect duplicates / ordering issues
        """

        try:
            raw_data, addr = sock.recvfrom(4096)
        except BlockingIOError:
            return None, None

        # size check
        if len(raw_data) > MAX_PACKET_SIZE:
            print("Packet too large from", addr)
            return None, addr

        # decode JSON
        try:
            packet = json.loads(raw_data.decode("utf-8"))
        except json.JSONDecodeError:
            print("Invalid JSON from", addr)
            return None, addr

        # structure validation
        if not isinstance(packet, dict):
            print("Invalid packet structure")
            return None, addr

        if "seq" not in packet or "type" not in packet or "data" not in packet:
            print("Malformed packet")
            return None, addr

        seq = packet["seq"]

        # optional: validate data type (recommended for games)
        if not isinstance(packet["data"], (dict, list, int, float, str, bool, type(None))):
            print("Unexpected data format")
            return None, addr

        last = self.last_received.get(addr)

        if last is not None:

            if seq == last:
                print("Duplicate packet")
                return None, addr

            if seq < last:
                print("Out of order packet")
                return None, addr

            if seq > last + 1:
                print(f"Missing packets from {addr}: expected {last+1}, got {seq}")

        # update last received sequence
        self.last_received[addr] = seq

        # return full structured message
        return {
            "type": packet["type"],
            "data": packet["data"],
            "seq": seq
        }, addr