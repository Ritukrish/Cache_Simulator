import random

# ==============================
# Cache Line
# ==============================
class CacheLine:
    def __init__(this):
        this.valid = False
        this.tag = None
        this.dirty = False
        this.access_time = 0
        this.arrival_time = 0

# ==============================
# Cache Simulator
# ==============================
class SetAssociativeCache:
    def __init__(this, config):
        this.cache_size = config["cache_size"]
        this.block_size = config["block_size"]
        this.assoc = config["associativity"]
        this.num_sets = this.cache_size // (this.block_size * this.assoc)

        this.write_policy = config["write_policy"]
        this.write_allocate = config["write_allocate"]
        this.replacement_policy = config["replacement_policy"]

        this.hit_time = config["hit_time"]
        this.miss_time = config["miss_time"]

        # Cache structure
        this.cache = [[CacheLine() for _ in range(this.assoc)] for _ in range(this.num_sets)]

        # Stats
        this.ticks = 0
        this.total = 0
        this.reads = 0
        this.writes = 0
        this.hits = 0
        this.misses = 0
        this.dirty_evictions = 0

        # Classification
        this.compulsory = 0
        this.conflict = 0
        this.capacity = 0
        this.seen_blocks = set()

        # Reference FA Cache (Size = total blocks in real cache)
        this.fa_capacity = this.cache_size // this.block_size
        this.fa_cache = [] 

    def update_fa_cache(this, block_addr):
        if block_addr in this.fa_cache:
            this.fa_cache.remove(block_addr)
        this.fa_cache.append(block_addr)
        if len(this.fa_cache) > this.fa_capacity:
            this.fa_cache.pop(0)

    def find_victim(this, set_index):
        lines = this.cache[set_index]
        if this.replacement_policy == "LRU":
            return min(range(this.assoc), key=lambda i: lines[i].access_time)
        elif this.replacement_policy == "FIFO":
            return min(range(this.assoc), key=lambda i: lines[i].arrival_time)
        else:
            return random.randint(0, this.assoc - 1)

    def access(this, op, address):
        this.total += 1
        this.ticks += 1
        if op == 'R': this.reads += 1
        else: this.writes += 1

        block_addr = address // this.block_size
        set_index = block_addr % this.num_sets
        tag = block_addr // this.num_sets
        
        set_lines = this.cache[set_index]
        hit_idx = -1

        for i, line in enumerate(set_lines):
            if line.valid and line.tag == tag:
                hit_idx = i
                break

        if hit_idx != -1:
            this.hits += 1
            set_lines[hit_idx].access_time = this.ticks
            if op == 'W' and this.write_policy == "write_back":
                set_lines[hit_idx].dirty = True
        else:
            this.misses += 1
            # Miss Classification
            if block_addr not in this.seen_blocks:
                this.compulsory += 1
                this.seen_blocks.add(block_addr)
            elif block_addr in this.fa_cache:
                this.conflict += 1
            else:
                this.capacity += 1

            # Allocation Logic
            if (op == 'R') or (op == 'W' and this.write_allocate):
                target_idx = -1
                for i, line in enumerate(set_lines):
                    if not line.valid:
                        target_idx = i
                        break
                
                if target_idx == -1:
                    target_idx = this.find_victim(set_index)
                    if set_lines[target_idx].dirty:
                        this.dirty_evictions += 1
                
                target = set_lines[target_idx]
                target.valid = True
                target.tag = tag
                target.arrival_time = this.ticks
                target.access_time = this.ticks
                target.dirty = (op == 'W' and this.write_policy == "write_back")

        this.update_fa_cache(block_addr)

# ==============================
# Execution Logic
# ==============================
def simulate(config_file, trace_file, output_file):
    config = {}
    with open(config_file, 'r') as f:
        for line in f:
            line = line.split('#')[0].strip()
            if '=' not in line: continue
            k, v = [x.strip() for x in line.split('=')]
            if k in ["cache_size", "block_size", "associativity", "address_bits"]:
                config[k] = int(v)
            elif k in ["hit_time", "miss_time"]:
                config[k] = float(v.split()[0])
            else:
                config[k] = (v.lower() == 'yes' if k == 'write_allocate' else v)

    cache = SetAssociativeCache(config)

    with open(trace_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(('#', '-')): continue
            parts = line.split()
            cache.access(parts[0].upper(), int(parts[1], 16))

    miss_rate = cache.misses / cache.total
    amat = config['hit_time'] + (miss_rate * config['miss_time'])

    with open(output_file, 'w') as out:
        out.write("Cache Configuration:\n")
        out.write(f"Cache Size: {config['cache_size'] // 1024} KB\n")
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
        out.write(f"Hit Rate: {(cache.hits/cache.total)*100:.2f}%\n")
        out.write(f"Miss Rate: {(cache.misses/cache.total)*100:.2f}%\n\n")
        out.write(f"AMAT: {amat:.2f} ns\n")

if __name__ == "__main__":
    simulate("config.txt", "LRU.txt", "LRU_o.txt")