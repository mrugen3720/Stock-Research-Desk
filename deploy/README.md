# Deploy: run the Discord bot 24/7 on a free Oracle Cloud VM

Goal: the bot runs always-on, with **no dependency on your Mac or a terminal**.
Free forever, never sleeps. One-time VM setup, then it looks after itself.

The bot uses Discord **long polling** (it dials OUT), so the server needs **no
public URL and no inbound ports** — just SSH for setup.

---

## 1. Create the free VM (one-time, in the Oracle web console)

1. Sign up at https://cloud.oracle.com — choose **Always Free**. (A card is
   required for identity verification only; the Always Free resources are never
   charged.)
2. **Compute → Create Instance:**
   - Shape: **Ampere (VM.Standard.A1.Flex)** — set **1 OCPU, 6 GB RAM**.
   - Image: **Canonical Ubuntu 24.04** (aarch64).
   - Save the **SSH private key** it gives you; note the instance's **public IP**.
   - If you see *"Out of host capacity"*, pick a different Availability Domain or
     try again later (ARM free capacity comes and goes).
3. Test SSH from your Mac:
   ```bash
   ssh -i /path/to/key ubuntu@<public-ip>
   ```

Leave the default firewall as-is (SSH/22 only). **Do not open other ports.**

## 2. Send the code + secrets from your Mac

From the project folder on your Mac (this copies the live code AND your `.env`,
and skips the Mac-only venv):

```bash
rsync -av --exclude venv --exclude __pycache__ --exclude .git \
  -e "ssh -i /path/to/key" ./ ubuntu@<public-ip>:~/stock-research-desk/
```

Then, on the VM, lock down the secrets file:
```bash
chmod 600 ~/stock-research-desk/.env
```

## 3. Install + start the bot (one command on the VM)

```bash
chmod +x ~/stock-research-desk/deploy/setup.sh
~/stock-research-desk/deploy/setup.sh
```

That builds the environment, installs dependencies, and registers the bot as a
systemd service that **auto-starts on boot and auto-restarts on crash**.

## 4. Verify

```bash
sudo systemctl status stock-bot     # -> active (running)
journalctl -u stock-bot -f          # -> "Discord bot ready as ... /stock synced"
```

Now **close your Mac terminal / turn the Mac off** and run `/stock reliance` in
your Discord server — you should still get a verdict.

Reboot test (proves it's truly hands-off): `sudo reboot`, wait, then
`sudo systemctl status stock-bot` should be running again on its own.

## 5. Updating later

When you change code on the Mac, re-send and restart:
```bash
# on the Mac
rsync -av --exclude venv --exclude __pycache__ --exclude .git \
  -e "ssh -i /path/to/key" ./ ubuntu@<public-ip>:~/stock-research-desk/
# on the VM
sudo systemctl restart stock-bot
```

---

### Notes / gotchas
- **Memory:** this app loads pandas + numpy + langgraph (~0.5–1 GB), which is why
  we use the 6 GB ARM VM, not a 256 MB free tier (those crash on startup).
- **ARM wheels:** if a package fails to build for lack of an ARM wheel (rare),
  run `sudo apt-get install -y rustc cargo` on the VM and re-run `setup.sh`.
- **Idle reclamation:** Oracle may reclaim *idle* free instances. A bot polling
  Discord 24/7 counts as active, so this normally isn't an issue; optionally keep
  a boot-volume backup so you can recreate quickly if it ever happens.
- **No-capacity fallback:** if you can't get a free ARM instance at all, the
  easiest paid alternative is Railway (~$5/mo): upload the repo, set the start
  command to `python -m src.bot.discord_bot`, paste the `.env` values as
  variables.
