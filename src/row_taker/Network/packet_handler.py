import json   # used to convert Python dictionaries ↔ JSON text

# Maximum safe UDP packet size (to avoid fragmentation on most networks)
MAX_PACKET_SIZE = 1200


class PacketManager:

    def __init__(self):
        # sequence number for packets we send
        # increases every time we send a packet
        self.send_sequence = 0

        # dictionary storing the last packet sequence received
        # key = client address
        # value = last sequence number received from that client
        self.last_received = {}

    def send_packet(self, sock, address, data):
        """
        Convert Python data to JSON, attach a sequence number,
        validate size, and send the packet via UDP
        """

        # create the packet structure
        # seq → sequence number for ordering packets
        # data → actual message content
        packet = {
            "seq": self.send_sequence,
            "data": data
        }

        # convert dictionary → JSON string → bytes
        encoded = json.dumps(packet).encode("utf-8")

        # check packet size to avoid UDP fragmentation
        if len(encoded) > MAX_PACKET_SIZE:
            raise ValueError("Packet too large")

        # send the packet to the target address
        sock.sendto(encoded, address)

        # increase sequence number for the next packet
        self.send_sequence += 1

    def receive_packet(self, sock):
        """
        Receive UDP packet, decode JSON,
        and check for duplicates or missing packets
        """

        # receive raw UDP data and the sender's address
        raw_data, addr = sock.recvfrom(4096)

        # check if packet exceeds maximum safe size
        if len(raw_data) > MAX_PACKET_SIZE:
            print("Packet too large from", addr)
            return None, addr

        try:
            # convert bytes → string → Python dictionary
            packet = json.loads(raw_data.decode("utf-8"))

        except json.JSONDecodeError:
            # packet is not valid JSON
            print("Invalid JSON from", addr)
            return None, addr

        # verify the packet is a dictionary
        if not isinstance(packet, dict):
            print("Invalid packet structure")
            return None, addr

        # ensure required fields exist
        if "seq" not in packet or "data" not in packet:
            print("Malformed packet")
            return None, addr

        # get the packet's sequence number
        seq = packet["seq"]

        # look up the last packet we received from this sender
        last = self.last_received.get(addr)

        # if we have seen packets from this sender before
        if last is not None:

            # if the sequence number is identical
            # it means the packet was duplicated
            if seq == last:
                print("Duplicate packet")
                return None, addr

            # if the sequence number is smaller
            # it means packets arrived out of order
            if seq < last:
                print("Out of order packet")
                return None, addr

            # if sequence jumps forward by more than 1
            # some packets were lost
            if seq > last + 1:
                print("Missing packets detected")

        # update the last received sequence number for this client
        self.last_received[addr] = seq

        # return the actual data part of the packet
        return packet["data"], addr