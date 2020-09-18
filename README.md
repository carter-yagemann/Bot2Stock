# Bot2Stock: On the Feasibility of Automating Stock Market Manipulation

This repository contains the data and code artifacts from the paper
"Bot2Stock: On the Feasibility of Automating Stock Market Manipulation" by
Carter Yagemann, Simon P. Chung, Erkam Uzun, Sai Ragam, Brendan Saltaformaggio,
and Wenke Lee.

The simulator used in the evaluation is a modified version of
[ABIDES](https://github.com/abides-sim/abides).

## Data Artifacts

* `./evaluation-number-bots.csv`: Evaluation for the impact of the number
of Bot2Stock bots on the botmaster's profit. CSV format, `num_bots` is the
number of Bot2Stock bots (excluding the botmaster), `delta` is the change
in the botmaster's cash before and after the attack.

* `./evaluation-latency.csv`: Evaluation for the impact of latency on the
botmaster's profit. CSV format, `lag_factor` is the latency factor applied
to the botmaster and bots relative to the background traders, for
sending a packet one-way, `delta` is the change in the botmaster's cash before
and after the attack.

* `./demo.mp4`: Demo video showing the PoC Bot2Stock malware in action.

## Code Artifacts

### Simulator

`./simulator` contains the code for running simulations, as seen in the paper.
The steps below have been tested on Debian Buster with Python3 and `virtualenv`
installed.

#### Setup

```bash
# if you do not already have virtualenv
sudo pip install virtualenv

cd simulator
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate
pip install -r requirements.txt
```
#### Known Issues & Workarounds

* Mac OS does not provide `nproc`, which breaks `b2s-test.sh` and `b2s-eval.sh`.
  A workaround is to replace `nproc` with `sysctl -n hw.logicalcpu` in both scripts.

#### Usage

To run 1 trial to test your setup:

```bash
cd simulator
source venv/bin/activate
./scripts/b2s-test.sh
```

**Note:** This script may take 10 to 30 minutes to run.

To run the full evaluation, as seen in the paper:

```bash
cd simulator
source venv/bin/activate
./scripts/b2s-eval.sh
```

**Note:** This script may take *several days* to run, depending on how
many CPU cores your system has. It will produce about *4GB* of data.

In both cases, the output will be a CSV formatted file, `~/b2s-eval.csv`,
which summarizes the raw logs written to `./simulator/log`. In the CSV
file, `num_bots` is the number of Bot2Stock bots used in the attack
(excluding botmaster), `profit-baseline` is the botmaster's profit
*without* using the bots (i.e., coincidental profit), `profit-attack`
is the profit *while using* the bots to manipulate the stock price, and
`delta` is `profit-attack - profit-baseline`.

### PoC Malware

`./poc-malware-src` contains the code used in the PoC malware demo. Unfortunately,
this demo requires two online accounts to be registered and several configuration
changes that are OS and browser dependent, making it hard to reproduce. We do our
best to outline the steps below and *will not provide further support.*

We also do not plan to automate these steps because the purpose of the demo is to
show that Bot2Stock is technically feasible to implement, **not** to release a
working malware into the wild.

#### Setup

At a high level, the steps are:

1. Setup squid with SSL-bumping and configure it to redirect HTTP(S) traffic to an
ICAP server.
2. Instrument a browser with selenium and configure it to use the squid proxy.
3. Create a new CA certificate and add it as a trusted CA to the browser.
4. Register accounts at [yahoo.in](https://yahoo.in) and [Investopedia](https://www.investopedia.com/simulator/).
5. Set `content_hacked` in `./poc-malware-src/icap server/icap_main.py` to the pre-attack HTML of content for
https://www.investopedia.com/simulator/trade/showopentrades.aspx. This is what will be shown to the "victim" if
they try to view their transaction history during the attack.
6. Create a cookie pickle containing session keys for the email and trading accounts. See selenium's documentation
for formatting details.
7. Start the ICAP server code (`icap_main.py`).
8. Launch the attack using the scripts in `./poc-malware-src/selenium`.

More details are provided below:

1. Install some required packages:

```bash
sudo apt install squid python-selenium firefox python python-pip openssl
sudo pip install icapserver
```

2. Replace `/etc/squid/squid.conf` with `./poc-malware-src/squid_config.txt`.

3. Create a SSL key and add a certificate authority to firefox:

```bash
mkdir -p /etc/squid/cert/
cd /etc/squid/cert/
# This puts the private key and the self-signed certificate in the same file
openssl req -new -newkey rsa:4096 -sha256 -days 365 -nodes -x509 -keyout myca.pem -out myca.pem

# Add new CA to linux and update (this may not work for all versions of Firefox)
sudo cp myca.pem /usr/local/share/ca-certificates
sudo update-ca-certificates
```

4. Reconfigure firefox to use the squid proxy: `HTTP Proxy: 127.0.0.1:3128`.

#### Usage

Start the ICAP proxy: `./poc-malware-src/icap server/icap_main.py`

Add filter to Yahoo email: `./poc-malware-src/selenium/sel_add_filter.py`

Remove filter: `./poc-malware-src/selenium/sel_remove_filter.py`

Place order on Investopedia simulator: `./poc-malware-src/selenium/sel_investopedia_buy.py`
