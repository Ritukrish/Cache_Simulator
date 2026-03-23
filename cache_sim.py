import random

# ==============================
# Cache Line
# ==============================
class CacheLine:
    def __init__(self):
        self.valid = 0
        self.tag = None
        self.dirty = 0
        self.time = 0   # for LRU/FIFO


# ==============================
# Read Config
# ==============================
def read_config(filename):
    config = {}
    with open(filename) as f:
        for line in f:
            line = line.split('#')[0].strip()
            if not line:
                continue

            key, val = [x.strip() for x in line.split('=')]

            if key in ["cache_size", "block_size", "associativity", "address_bits"]:
                config[key] = int(val)

            elif key in ["hit_time", "miss_time"]:
                config[key] = float(val.split()[0])

            elif key == "write_allocate":
                config[key] = (val.lower() == "yes")

            else:
                config[key] = val

    return config


# ==============================
# Cache Simulator
# ==============================
class SetAssociativeCache:

    def __init__(self, config):

        self.cache_size = config["cache_size"]
        self.block_size = config["block_size"]
        self.assoc = config["associativity"]

        self.num_sets = self.cache_size // (self.block_size * self.assoc)

        self.write_policy = config["write_policy"]
        self.write_allocate = config["write_allocate"]
        self.replacement_policy = config["replacement_policy"]

        self.hit_time = config["hit_time"]
        self.miss_time = config["miss_time"]

        self.cache = [[CacheLine() for _ in range(self.assoc)] for _ in range(self.num_sets)]

        # Statistics
        self.time = 0
        self.total = 0
        self.reads = 0
        self.writes = 0
        self.hits = 0
        self.misses = 0
        self.dirty_evictions = 0

        self.compulsory = 0
        self.conflict = 0
        self.capacity = 0

        self.seen_blocks = set()

        # Fully associative simulation
        self.fa_cache = set()
        self.fa_capacity = (self.cache_size // self.block_size)


    # ==============================
    # Replacement selection
    # ==============================
    def choose_victim(self, set_lines):

        if self.replacement_policy == "LRU":
            return min(set_lines, key=lambda x: x.time)

        elif self.replacement_policy == "FIFO":
            return min(set_lines, key=lambda x: x.time)

        else:  # Random
            return random.choice(set_lines)


    # ==============================
    # Access Function
    # ==============================
    def access(self, op, address):

        self.total += 1
        self.time += 1

        block_addr = address // self.block_size
        set_index = block_addr % self.num_sets
        tag = block_addr // self.num_sets

        set_lines = self.cache[set_index]

        if op == 'R':
            self.reads += 1
        else:
            self.writes += 1


        # ==========================
        # HIT CHECK
        # ==========================
        for line in set_lines:

            if line.valid and line.tag == tag:

                self.hits += 1
                line.time = self.time

                if op == 'W' and self.write_policy == "write_back":
                    line.dirty = 1

                return


        # ==========================
        # MISS
        # ==========================
        self.misses += 1


        # Miss Classification
        if block_addr not in self.seen_blocks:

            self.compulsory += 1
            self.seen_blocks.add(block_addr)

        else:

            if len(self.fa_cache) < self.fa_capacity:
                self.conflict += 1
            else:
                self.capacity += 1


        # Fully associative update
        if len(self.fa_cache) >= self.fa_capacity:
            self.fa_cache.pop()

        self.fa_cache.add(block_addr)


        # ==========================
        # Find Empty or Victim
        # ==========================
        empty_line = next((l for l in set_lines if not l.valid), None)

        if empty_line:
            target = empty_line
        else:
            target = self.choose_victim(set_lines)

            if target.dirty:
                self.dirty_evictions += 1


        # ==========================
        # WRITE MISS
        # ==========================
        if op == 'W':

            if self.write_policy == "write_through":

                if self.write_allocate:
                    self.load(target, tag)

            elif self.write_policy == "write_back":

                if self.write_allocate:
                    self.load(target, tag)
                    target.dirty = 1


        # ==========================
        # READ MISS
        # ==========================
        else:

            self.load(target, tag)


    # ==============================
    # Load block into cache
    # ==============================
    def load(self, line, tag):

        line.valid = 1
        line.tag = tag
        line.dirty = 0
        line.time = self.time



# ==============================
# Simulation Runner
# ==============================
def simulate(config_file, trace_file, output_file):

    config = read_config(config_file)
    cache = SetAssociativeCache(config)

    with open(trace_file) as f:

        for line in f:

            line = line.strip()
            if not line:
                continue

            op, addr = line.split()

            address = int(addr, 16)

            cache.access(op, address)


    hit_rate = cache.hits / cache.total
    miss_rate = cache.misses / cache.total

    amat = cache.hit_time + (miss_rate * cache.miss_time)


    with open(output_file, "w") as out:

        out.write("Cache Configuration:\n")

        out.write(f"Cache Size: {config['cache_size']} B\n")
        out.write(f"Block Size: {config['block_size']} B\n")
        out.write(f"Associativity: {config['associativity']}-way\n")
        out.write(f"Replacement: {config['replacement_policy']}\n")
        out.write(f"Write Policy: {config['write_policy']}\n")
        out.write(f"Write Allocate: {'yes' if config['write_allocate'] else 'no'}\n\n")

        out.write("Results:\n")

        out.write(f"Total Accesses: {cache.total}\n")
        out.write(f"Reads: {cache.reads}\n")
        out.write(f"Writes: {cache.writes}\n\n")

        out.write(f"Hits: {cache.hits}\n")
        out.write(f"Misses: {cache.misses}\n")
        out.write(f"Dirty Evictions: {cache.dirty_evictions}\n\n")

        out.write(f"Compulsory Misses: {cache.compulsory}\n")
        out.write(f"Conflict Misses: {cache.conflict}\n")
        out.write(f"Capacity Misses: {cache.capacity}\n\n")

        out.write(f"Hit Rate: {hit_rate*100:.2f}%\n")
        out.write(f"Miss Rate: {miss_rate*100:.2f}%\n\n")

        out.write(f"AMAT: {amat:.2f} ns\n")


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":

    simulate("config.txt", "trace.txt", "Test1_WB_WA.txt")