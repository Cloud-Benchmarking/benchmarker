import argparse
import concurrent
import concurrent.futures
import glob
import queue
import random

import itertools
import re
import shutil
import time
import traceback
import uuid
from datetime import datetime
from distutils import dir_util
from enum import Enum
from multiprocessing.dummy import freeze_support
from pprint import pprint
from typing import AnyStr, List, NamedTuple
import logging
import humanize
from python_terraform import *
from tqdm import tqdm


COHORT = "all-providers-real"


class CloudProvider(str, Enum):
    AZURE = "azure"
    LINODE = "linode"
    DIGITALOCEAN = "digitalocean"
    VULTR = "vultr"
    # OVH = 'ovh'
    GCP = "gcp"
    AWS = "aws"

    @staticmethod
    def ssh_user(provider: str):
        if provider == CloudProvider.AZURE.value:
            return "azureroot"
        elif provider == CloudProvider.AWS.value:
            return "ubuntu"

        return "root"

    def __str__(self):
        return self.value


class BenchmarkHost(NamedTuple):
    provider: CloudProvider
    region: str
    zone: str = None

    def zoneless(self) -> str:
        return str(BenchmarkHost(self.provider, self.region, None))

    def __str__(self) -> str:
        base_str = f"{self.provider}+{self.region}"
        if self.zone is not None and len(self.zone) > 0 and (self.zone != self.region):
            return f"{base_str}[{self.zone}]"
        return base_str


class BenchmarkConfig(NamedTuple):
    hosts: List[BenchmarkHost]

    def __str__(self):
        return "_".join([str(h) for h in self.hosts])


class BenchmarkTarget(NamedTuple):
    src_dst: AnyStr
    ip_address: AnyStr
    private_ip_address: AnyStr
    region: AnyStr
    zone: AnyStr
    provider: AnyStr
    ssh_private_key: AnyStr

    def ssh_keygen_reset(self):
        cmd = ["ssh-keygen", "-R", self.ip_address]
        p = subprocess.run(
            cmd, capture_output=True, cwd=os.path.dirname(self.ssh_private_key)
        )
        return (
            p.returncode,
            str(p.stdout.decode("ascii")),
            str(p.stderr.decode("ascii")),
        )

    def run_ssh_cmd(self, cmd_str):
        username = CloudProvider.ssh_user(self.provider)
        cmd = [
            "ssh",
            "-i",
            os.path.basename(self.ssh_private_key),
            "-o",
            "StrictHostKeyChecking=no",
            f"{username}@{self.ip_address}",
        ]
        cmd.extend(cmd_str.split())
        p = subprocess.run(
            cmd, capture_output=True, cwd=os.path.dirname(self.ssh_private_key)
        )
        return (
            p.returncode,
            str(p.stdout.decode("ascii")),
            str(p.stderr.decode("ascii")),
        )

    def run_ssh_benchmark_cmd(self, cmd_str, as_private=False):
        stdout_all = []
        stderr_all = []
        # run a hostname since these lots may be written to the same file
        # this let's us know which machine is under execution a bit easier
        # to read than just the IP address
        (return_code, stdout, stderr) = self.run_ssh_cmd(f"hostname")
        stdout_all.append(stdout)
        stderr_all.append(stderr)

        (return_code, stdout, stderr) = self.run_ssh_cmd(f"time {cmd_str}")
        stdout_all.append(stdout)
        stderr_all.append(stderr)
        return (return_code, "\n".join(stdout_all), "\n".join(stderr_all))


def run_ssh_cmd(ip_str, cmd_str, id_rsa_path):
    cmd = [
        "ssh",
        "-i",
        os.path.basename(id_rsa_path),
        "-o",
        "StrictHostKeyChecking=no",
        f"root@{ip_str}",
    ]
    cmd.extend(cmd_str.split())
    p = subprocess.run(cmd, capture_output=True, cwd=os.path.dirname(id_rsa_path))
    return (p.returncode, str(p.stdout.decode("ascii")), str(p.stderr.decode("ascii")))


def run_ssh_benchmark_cmd(ip_str, cmd_str, id_rsa_path):
    stdout_all = []
    stderr_all = []
    # run a hostname since these lots may be written to the same file
    # this let's us know which machine is under execution a bit easier
    # to read than just the IP address
    (return_code, stdout, stderr) = run_ssh_cmd(ip_str, f"hostname", id_rsa_path)
    stdout_all.append(stdout)
    stderr_all.append(stderr)

    (return_code, stdout, stderr) = run_ssh_cmd(ip_str, f"time {cmd_str}", id_rsa_path)
    stdout_all.append(stdout)
    stderr_all.append(stderr)
    return (return_code, "\n".join(stdout_all), "\n".join(stderr_all))


IPERF_PORT = 20000
IPERF_UDP_PORT = 25000
IPERF_RETRIES = 5
BENCHMARK_RUNTIME = 60
THREAD_COUNT = 1


def run_iperf(targets: List[BenchmarkTarget], private=False):
    stdout_all = []
    stderr_all = []
    try:
        for target in targets:
            (return_code, stdout, stderr) = target.run_ssh_cmd(
                f"sudo nohup iperf --server --port {IPERF_PORT} &> /dev/null & echo $!"
            )
            stdout_all.append(stdout)
            stderr_all.append(stderr)

        bench_start = time.perf_counter()
        for from_host, to_host in targets, reversed(targets):
            to_ip = to_host.private_ip_address if private else to_host.ip_address
            # TODO: fix for azure
            # (return_code, stdout, stderr) = _run_iperf(from_host.ip_address, to_ip, from_host.ssh_private_key)
            (return_code, stdout, stderr) = from_host.run_ssh_cmd(
                f"sudo iperf --enhancedreports --client {to_ip} --port {IPERF_PORT} --format m --time {BENCHMARK_RUNTIME} --parallel {THREAD_COUNT}"
            )

            stdout_all.append(stdout)
            stderr_all.append(stderr)
        bench_end = time.perf_counter()
        print(
            f"Benchmark total time: {bench_end - bench_start:0.4f} seconds", flush=True
        )
        print(
            f"Benchmark total time: {humanize.naturaltime(bench_end - bench_start)}",
            flush=True,
        )
    except Exception as ex:
        stderr_all.append(str(ex))

    return (0, "\n".join(stdout_all), "\n".join(stderr_all))


def run_ping(targets: List[BenchmarkTarget]):
    stdout_all = []
    stderr_all = []
    try:
        bench_start = time.perf_counter()
        for from_host, to_host in targets, reversed(targets):
            logging.info(f"_run_ping({from_host}, {to_host})")
            ping_cmd = f"ping -c 100 {to_host.ip_address}"
            stdout_all.append(ping_cmd)
            (return_code, stdout, stderr) = from_host.run_ssh_cmd(ping_cmd)
            stdout_all.append(stdout)
            stderr_all.append(stderr)
        bench_end = time.perf_counter()
        print(f"Ping total time: {bench_end - bench_start:0.4f} seconds", flush=True)
        print(
            f"Ping total time: {humanize.naturaltime(bench_end - bench_start)}",
            flush=True,
        )
    except Exception as ex:
        stderr_all.append(str(ex))

    return (0, "\n".join(stdout_all), "\n".join(stderr_all))


def run_traceroute(targets: List[BenchmarkTarget], use_icmp=False, private=False):
    stdout_all = []
    stderr_all = []
    try:
        bench_start = time.perf_counter()
        trace_type = "icmp" if use_icmp else "udp"
        for from_host, to_host in targets, reversed(targets):
            logging.info(f"_run_traceroute({from_host}, {to_host})")
            to_ip = to_host.private_ip_address if private else to_host.ip_address
            traceroute_cmd = f"sudo traceroute --tries=5 --wait=5 --resolve-hostnames --type={trace_type} {to_ip}"
            stdout_all.append(traceroute_cmd)
            (return_code, stdout, stderr) = from_host.run_ssh_cmd(traceroute_cmd)
            stdout_all.append(stdout)
            stderr_all.append(stderr)
        bench_end = time.perf_counter()
        print(
            f"Benchmark total time: {bench_end - bench_start:0.4f} seconds", flush=True
        )
        print(
            f"Benchmark total time: {humanize.naturaltime(bench_end - bench_start)}",
            flush=True,
        )
    except Exception as ex:
        stderr_all.append(str(ex))

    return (0, "\n".join(stdout_all), "\n".join(stderr_all))


def run_cryptsetup_benchmark(targets: List[BenchmarkTarget]):
    stdout_all = []
    stderr_all = []
    try:
        bench_start = time.perf_counter()
        for target in targets:
            logging.info(f"_run_cryptsetup_benchmark({target})")
            (return_code, stdout, stderr) = target.run_ssh_benchmark_cmd(
                "cryptsetup benchmark"
            )
            stdout_all.append(stdout)
            stderr_all.append(stderr)
        bench_end = time.perf_counter()
        print(
            f"Benchmark total time: {bench_end - bench_start:0.4f} seconds", flush=True
        )
        print(
            f"Benchmark total time: {humanize.naturaltime(bench_end - bench_start)}",
            flush=True,
        )
    except Exception as ex:
        stderr_all.append(str(ex))

    return (0, "\n".join(stdout_all), "\n".join(stderr_all))


def choose_random_zone(provider: str, region: str):
    regions_to_zones = json.load(
        open(os.path.join("artifacts", "regions", "regions-to-zones.json"), "r")
    )
    if provider in regions_to_zones and region in regions_to_zones[provider]:
        zones = regions_to_zones[provider][region]
        return zones[random.randint(0, len(zones) - 1)]
    return None


class BenchmarkRunner(object):
    config: BenchmarkConfig
    tf: Terraform
    uuid: uuid.UUID
    tf_work_dir: AnyStr
    benchmark_dir: AnyStr
    targets: List[BenchmarkTarget]
    enable_private_networking: bool

    def __init__(self, config_str: str):
        self.config_str = config_str
        self.config = decode_combo_str(config_str)
        self.uuid = uuid.uuid4()
        self.targets = []

        if (len(self.config.hosts) == 2) and (len(set(self.config.hosts)) == 1):
            self.enable_private_networking = True
        else:
            self.enable_private_networking = False

    def write_to_logfile(self, name, stdout, stderr, print_logs: bool = False):
        # ensure we're always writing a single string block
        if isinstance(stdout, list):
            stdout = "\n".join(stdout)
        if isinstance(stderr, list):
            stderr = "\n".join(stderr)

        # write the actual log files
        with open(
            os.path.join(self.benchmark_dir, f"{name}.stdout.log"),
            "w",
            encoding="utf-8",
        ) as fp:
            fp.write(stdout)
        with open(
            os.path.join(self.benchmark_dir, f"{name}.stderr.log"),
            "w",
            encoding="utf-8",
        ) as fp:
            fp.write(stderr)

        # if requested, print out stdout
        if print_logs:
            print(stdout, flush=True)
        # always print errors
        print(stderr, flush=True)

    def fix_line_endings(self, file_path):
        with open(file_path, "rb") as open_file:
            content = open_file.read()

        content = content.replace(b"\r\n", b"\n")

        with open(file_path, "wb") as open_file:
            open_file.write(content)

    def init_tf(self):
        # print("making tfworkdir", flush=True)
        tf_dir = os.path.abspath("terraform")

        # make sure provision script isn't corrupted by windows
        self.fix_line_endings(os.path.join(tf_dir, "provision-benchmark-node.sh"))

        self.tf_work_dir = os.path.abspath(
            os.path.join(".tfworkdir", "benchmarks", str(self.uuid))
        )
        if not os.path.exists(self.tf_work_dir):
            os.makedirs(self.tf_work_dir)

        # print("copy_tree tfworkdir", flush=True)
        dir_util.copy_tree(tf_dir, self.tf_work_dir)
        if os.path.exists(os.path.join(self.tf_work_dir, ".terraform")):
            dir_util.remove_tree(os.path.join(self.tf_work_dir, ".terraform"))

        # Do string substitution on the main Terraform file.
        #
        # This isn't great but is a "solution" to the problem that Terraform doesn't allow module sources to be variables/interpolated.
        # An alternative method would be to make main.tf a jinja2 template and render it, but then editing the main.tf becomes
        # a pain in any IDE since it will be treated either as a jinja2 template and lose intellisense, or like a Terraform file
        # which has syntax errors onlines like `source = {{ module_src }}`.
        main_tf = open(os.path.join(self.tf_work_dir, "main.tf"), "r").read()
        main_tf_updated = main_tf.replace(
            'source = "./modules/null"',
            f'source = "./modules/{self.config.hosts[0].provider}"',
            1,
        )
        main_tf_updated = main_tf_updated.replace(
            'source = "./modules/null"',
            f'source = "./modules/{self.config.hosts[1].provider}"',
            1,
        )
        with open(os.path.join(self.tf_work_dir, "main.tf"), "w") as fp:
            fp.write(main_tf_updated)

        tf_vars = os.path.abspath(os.path.join(self.tf_work_dir, "terraform.tfvars"))
        self.tf = Terraform(
            working_dir=self.tf_work_dir,
            var_file=tf_vars,
            variables={
                "src_region": self.config.hosts[0].region,
                "dst_region": self.config.hosts[1].region,
                "src_zone": self.config.hosts[0].zone,
                "dst_zone": self.config.hosts[1].zone,
                "uuid_partial": str(self.uuid).split("-")[-1],
                "enable_private_networking": self.enable_private_networking,
            },
        )

        self.tf.init()

    def provision(self):
        return_code, stdout, stderr = self.tf.apply(capture_output=True, skip_plan=True)
        # stdout = [self.config_str, stdout]
        self.write_to_logfile("apply", stdout, stderr, print_logs=False)

        # use copy2 to preserve original file metadata
        tfstate_filepath = os.path.join(
            os.path.abspath(self.benchmark_dir), "terraform.tfstate"
        )
        shutil.copy2(
            os.path.join(self.tf_work_dir, "terraform.tfstate"), tfstate_filepath
        )

        # initialize our targets
        for target_type, config in self.tf.tfstate.outputs["benchmark_targets"][
            "value"
        ].items():
            self.targets.append(
                BenchmarkTarget(
                    src_dst=target_type,
                    ip_address=config["ip_address"],
                    private_ip_address=config["private_ip_address"],
                    provider=config["provider"],
                    region=config["region"],
                    zone=config["zone"],
                    ssh_private_key=os.path.join(
                        os.path.abspath(self.tf.working_dir),
                        config["ssh_private_key"].split("/")[-1],
                    ),
                )
            )

        # often get the same IP from a provider during many runs
        # so a recycled IP will have a different ssh public key fingerprint
        # do a reset for the IP and we should be good
        for target in self.targets:
            target.ssh_keygen_reset()

        # save the "who is who" data for easier parsing/debugging later
        self.write_to_logfile("targets", json.dumps(self.targets), "", print_logs=True)

    def run_ssh_cmd_host(self, target: BenchmarkTarget, cmd: str):
        pass

    def run_demographics(self):
        try:
            name_demo_cmds = {
                "lshw": "sudo lshw -json",
                "cpuid": "sudo cpuid -1",
                "cpuinfo": "sudo cat /proc/cpuinfo",
                "ifconfig": "sudo ifconfig",
                "resolvectl": "sudo resolvectl status",
            }
            for name, cmd in name_demo_cmds.items():
                for target in self.targets:
                    (return_code, stdout, stderr) = target.run_ssh_cmd(cmd)
                    self.write_to_logfile(f"{name}.{target.src_dst}", stdout, stderr)
        except Exception as ex:
            print(f"TODO: run_demographics - NEED TO TAKE CARE OF THIS EXCEPTION: {ex}")

    def run_benchmarks(self):
        return_code, stdout, stderr = run_ping(self.targets)
        self.write_to_logfile("ping", stdout, stderr, print_logs=True)

        if CloudProvider.AZURE.value in [t.provider for t in self.targets]:
            self.write_to_logfile(
                "traceroute.skip",
                "Skipping traceroute because of Azure",
                "stderr",
                print_logs=True,
            )
        else:
            return_code, stdout, stderr = run_traceroute(self.targets)
            self.write_to_logfile("traceroute", stdout, stderr, print_logs=True)

            return_code, stdout, stderr = run_traceroute(self.targets, use_icmp=True)
            self.write_to_logfile("traceroute.icmp", stdout, stderr, print_logs=True)

            if self.enable_private_networking:
                return_code, stdout, stderr = run_traceroute(self.targets, private=True)
                self.write_to_logfile(
                    "traceroute.private", stdout, stderr, print_logs=True
                )
                return_code, stdout, stderr = run_traceroute(
                    self.targets, use_icmp=True, private=True
                )
                self.write_to_logfile(
                    "traceroute.private.icmp", stdout, stderr, print_logs=True
                )

        return_code, stdout, stderr = run_iperf(self.targets)
        self.write_to_logfile("iperf", stdout, stderr, print_logs=True)

        if self.enable_private_networking:
            return_code, stdout, stderr = run_iperf(self.targets, private=True)
            self.write_to_logfile("iperf.private", stdout, stderr, print_logs=True)

        return_code, stdout, stderr = run_cryptsetup_benchmark(self.targets)
        self.write_to_logfile("cryptsetup_benchmark", stdout, stderr, print_logs=True)

    def cleanup(self):
        return_code, stdout, stderr = self.tf.destroy(capture_output=True, force=True)
        self.write_to_logfile("destroy", stdout, stderr, print_logs=False)

        # sometimes [WinError 145] The directory is not empty
        # ignore errors and delete anyways
        # Windows is dumb
        try:
            shutil.rmtree(self.tf_work_dir, ignore_errors=True)
            dir_util.remove_tree(self.tf_work_dir)
        except:
            pass

    def run(self):
        start_all = time.perf_counter()
        # todo: add config values to
        try:
            # get terraform
            print(
                f"[{str(self.config)}] starting {self.uuid} @ {datetime.now()}",
                flush=True,
            )

            # print("making benchmark_dir", flush=True)
            self.benchmark_dir = os.path.join(
                "artifacts",
                COHORT,
                self.config_str.replace("|", "_").replace(":", "-"),
                str(self.uuid),
            )
            if not os.path.exists(self.benchmark_dir):
                os.makedirs(self.benchmark_dir)

            self.init_tf()

            # tf cant handle tfplans in different dirs apparently
            tfplan_filepath = os.path.join(f"{self.uuid}.tfplan")
            self.tf.plan(capture_output=False, out=tfplan_filepath)
            shutil.move(
                os.path.join(self.tf_work_dir, tfplan_filepath),
                os.path.join(self.benchmark_dir, tfplan_filepath),
            )

            # provision
            self.provision()

            # do vm/hw survey
            self.run_demographics()

            # run benchmarks
            self.run_benchmarks()

            # run geekbench
            # for target in self.targets:
            #     (return_code, stdout, stderr) = target.run_ssh_cmd("~/Geekbench-5.3.2-Linux/geekbench5")
            #     self.write_to_logfile(f'geekbench.{target.src_dst}', stdout, stderr, print_logs=True)

        except Exception as ex:
            print(
                f"TODO: run - NEED TO TAKE CARE OF THIS EXCEPTION: {traceback.format_exc()}"
            )

        finally:
            # cleanup
            self.cleanup()

            end_all = time.perf_counter()
            print(
                f"[{str(self.config)}] ending {self.uuid} @ {datetime.now()}",
                flush=True,
            )
            print(f"Total time: {end_all - start_all:0.4f} seconds")
            print(f"Total time: {humanize.naturaltime(end_all - start_all)}")


def decode_combo_str(combo: str) -> BenchmarkConfig:
    hosts = combo.split("_")
    parsed_hosts = []
    for h in hosts:
        provider, region = h.split("+")
        zone_parts = region.split("[")
        zone = choose_random_zone(provider, region)

        if len(zone_parts) > 1:
            region = zone_parts[0]
            zone = zone_parts[1].replace("]", "")

        parsed_hosts.append(
            BenchmarkHost(provider=CloudProvider(provider), region=region, zone=zone)
        )
    return BenchmarkConfig(hosts=parsed_hosts)


def get_provider_regions(provider):
    return list(
        json.load(open(os.path.join("artifacts", "all_regions.json"), "r"))[
            provider.value
        ].keys()
    )


def build_combos(provider, round_robin=True):
    combos = []
    provider_regions = get_provider_regions(provider)
    combos.extend(zip(provider_regions, provider_regions))
    if round_robin:
        combos.extend(list(itertools.combinations(provider_regions, 2)))
    benchmarks_to_run = []
    for combo in combos:
        benchmarks_to_run.append(
            str(
                BenchmarkConfig(
                    hosts=[
                        BenchmarkHost(provider=provider, region=combo[0]),
                        BenchmarkHost(provider=provider, region=combo[1]),
                    ]
                )
            )
        )
    return benchmarks_to_run


def run_benchmark_str(benchmark_str) -> bool:
    print(f"{benchmark_str}")
    if os.path.exists(".killswitch") and open(
        ".killswitch", "r"
    ).read().strip().lower() in ["1", "true", "y", "yes", "engaged"]:
        print("killswitch activated, exiting", flush=True)
        return False

    start = time.perf_counter()
    try:
        runner = BenchmarkRunner(benchmark_str)
        runner.run()
    except Exception as ex:
        print(f"OH FUCK OH FUCK OH FUCK: {runner.config}: {ex}")
        print(f"{traceback.format_exc()}")
        return False
    end = time.perf_counter()
    print(f"Benchmark time: {end - start:0.4f} seconds")
    print(f"Benchmark time: {humanize.naturaltime(end - start)}")
    return True


def run_benchmark_strs_parallel(benchmark_strs, workers=8):
    freeze_support()
    print(
        f"Starting processing of {len(benchmark_strs)} regions with {workers} workers"
    )
    start = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        r = list(
            tqdm(
                executor.map(run_benchmark_str, benchmark_strs),
                total=len(benchmark_strs),
            )
        )
    end = time.perf_counter()
    print(f"Total time: {end - start:0.4f} seconds")
    print(f"Total time: {humanize.naturaltime(end - start)}")


def do_queue_processing(combos):
    combo_queue = queue.Queue()
    for combo in combos:
        combo_queue.put(combo)
    print(f"Total benchmarking combos: {combo_queue.qsize()}")
    start = time.perf_counter()
    run = not combo_queue.empty()
    queue_runs = 0
    while run:
        combo = combo_queue.get()
        queue_runs += 1
        if combo is None:
            exit()
        print(f"[{queue_runs}: {combo}")
        resp = run_benchmark_str(combo)
        if resp:
            combo_queue.task_done()
        else:
            combo_queue.put(combo)
        run = not combo_queue.empty()
    end = time.perf_counter()
    print(f"Total queue time: {end - start:0.4f} seconds")
    print(f"Total queue time: {humanize.naturaltime(end - start)}")
    pprint(combos)
    run_benchmark_str(combos[0])


def run_unfinished_cohort():
    combo_dirs = glob.glob(os.path.join("artifacts", COHORT, "*"))
    invalid_runs = []
    for combo_dir in combo_dirs:
        has_valid_run = False
        benchmark_config = decode_combo_str(os.path.basename(combo_dir))
        for dir in sorted(
            glob.glob(os.path.join(combo_dir, "*")), key=os.path.getmtime
        ):
            if os.path.exists(os.path.join(dir, "iperf.stdout.log")):
                has_valid_run = True
                break
        if not has_valid_run:
            invalid_runs.append(str(benchmark_config))
    print(f"[*] Missing {len(invalid_runs)} runs from {COHORT}")
    run_benchmark_strs_parallel(invalid_runs, workers=8)


def direct(args):
    if args.combo_file is not None:
        combos = [
            combo.strip()
            for combo in open(os.path.abspath(args.combo_file), "r").read().split()
        ]
    else:
        combos = args.combos

    run_benchmark_strs_parallel(combos, workers=args.workers)


def proxy(args):
    print("TODO: implement")


def generate_combos(args):
    # use all providers if none specified
    if args.providers is None or len(args.providers) == 0:
        args.providers = [p.value for p in CloudProvider]

    # grab all regions and cache which provider they belong to
    regions = {}
    for provider in args.providers:
        for provider_region in get_provider_regions(CloudProvider(provider)):
            regions[provider_region] = provider

    # build out the combinations of regions
    combos = []
    combos.extend(zip(regions.keys(), regions.keys()))
    if not args.skip_round_robin:
        combos.extend(list(itertools.combinations(regions.keys(), 2)))

    # parse into benchmark config strings
    benchmarks_to_run = []
    for combo in combos:
        benchmarks_to_run.append(
            str(
                BenchmarkConfig(
                    hosts=[
                        BenchmarkHost(provider=regions[combo[0]], region=combo[0]),
                        BenchmarkHost(provider=regions[combo[1]], region=combo[1]),
                    ]
                )
            )
        )

    # dump to screen
    print("\n".join(benchmarks_to_run))

    return benchmarks_to_run


def add_global_arguments(subparser):
    subparser.add_argument("--workers", dest="workers", default=1, type=int, help="")
    subparser.add_argument("--combos", nargs="+", dest="combos", help="bar help")
    subparser.add_argument("--cohort", nargs="+", dest="cohort", help="bar help")
    subparser.add_argument("--combo-file", dest="combo_file", help="")

    return subparser


def build_parser():
    parser = argparse.ArgumentParser(description="Process some integers.")
    subparsers = parser.add_subparsers(help="sub-command help", dest="subparser_name")

    parser_a = add_global_arguments(subparsers.add_parser("direct", help="a help"))
    parser_a.set_defaults(func=direct)

    parser_b = add_global_arguments(subparsers.add_parser("proxy", help="b help"))
    parser_b.set_defaults(func=proxy)

    parser_b = subparsers.add_parser("generate-combos", help="b help")
    parser_b.add_argument(
        "--providers",
        nargs="+",
        choices=[p.value for p in CloudProvider],
        help="baz help",
    )
    parser_b.add_argument("--skip-round-robin", action="store_true", default=False)
    parser_b.set_defaults(func=generate_combos)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    if args.subparser_name in ["direct", "proxy"]:
        if (args.combos is None) and (args.combo_file is None):
            parser.error("either a combo file or combo list is required")
    args.func(args)
