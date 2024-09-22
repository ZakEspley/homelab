# homelab
Just stuff I use for my homelab

| Relevant | Info |
| --- | --- |
| OS Type| 64-Bit Raspbian OS Bookworm Lit|
| Hostname| dirac |
| External Drive Moutning Point| `/mnt/ext1`|
| Docker Data Location| `/mnt/ext1/docker`|
| Portainer Data Location| `/mnt/ext1/portainer/data`|
| Nextcloud-aio Port | 11000 |
| Portainer Port | 9443|


## Migrating to 64 bit Raspbian OS Bookworm

1. Used Raspberry Pi Imager to put on Raspberry Pi OS Lite Bookworm
2. Create automatic external drive mounting
3. Install Docker
4. Install Portainer
5. Install Cloudflare Tunnel
6. Install Nextcloud-aio
7. Install Vaultwarden
8. Install Watchtower


### 1. Flash Raspbian Pi OS Lite
I just downloaded the latest Raspberry Pi Os Imager on my Windows Machine and installed it onto a 64GB MicroSD. Then put it into the Pi, boot it and wait a few minutes. Then ssh in and run 

```bash
sudo apt update
sudo apt upgrade
```

### 2. Auto Mounting My External SSD
First you need to create a mount on the drive to mount the harddrive. I choose to do this at `/mnt/ext1`. So I ran
```bash
sudo mkdir /mnt/ext1
```

I followed [this guide for endevourOS](https://forum.endeavouros.com/t/tutorial-how-to-permanently-mount-external-internal-drives-in-linux/18688)

Plug in the SSD if it is not aleady plugged in and then run
```bash
blkid
```
And copy the UUID of the drive. It us usually something like /dev/sda1. Then run

```bash
sudo nano /etc/fstab
```
and add the following line at the bottom to use systemd to automount the drive to mount it to `/mnt/ext1` as `ext4` drive.
```bash
UUID=<UUID of your external device> /mnt/ext1      ext4    noatime,x-systemd.automount,x-systemd.device-timeout=10,x-systemd.idle-timeout=1min 0 2
```

Then you need to run
```bash
sudo systemctl daemon-reload
```

Followed by
```bash
sudo mount -a
```


### 3. Installing Docker
At the time of writing, when installing docker on 64 but Raspbian OS we must use the [Debian instrucions](https://docs.docker.com/engine/install/debian/). The instructions say to run the following codes:

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```
Then run

``` bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

The last step is to move the data directory of docker onto the external drive. We do this by following [this guide](https://www.guguweb.com/2019/02/07/how-to-move-docker-data-directory-to-another-location-on-ubuntu/). We first need to create a location on the drive in which to hold the files. I choose that to be `/mnt/ext1/docker`. So make that directory by running

```bash
sudo mkdir /mnt/ext1/docker
```
if it is not already made.

Then the guide says to run the following commands
```bash
sudo service docker stop
```
```bash
sudo nano /etc/docker/daemon.json
```
Then add the following line
```json
{
  "data-root": "/mnt/ext1/docker"
}
```
Copy the current docker directory to the new location

```bash
sudo rsync -aP /var/lib/docker/ /mnt/ext1/docker/
```
Rename the old docker info
```bash
sudo mv /var/lib/docker /var/lib/docker.old
```
Test it out by running
```bash
sudo service docker start
```
If all is well then you can remove the folder from before
```bash
sudo rm -rf /var/lib/docker.old
```
### 4. Install Portainer
I ran the following docker command, which creates a mounting point at `/mnt/ext1/portainer/data` because that is what I did before I knew how to move the docker data directory. I am not 100% that this is the best but I am going to keep it since I already have things set up to work that way.

```bash
sudo docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v /mnt/ext1/portainer/data:/data portainer/portainer-ce:2.21.1
```

Once it it runs you open a browser and go to https://dirac.local:9443 to finish the setup.

### Installing Cloudflare Tunnel
The next step will be to install a Cloudflare Tunnel. I already have everything created on Cloudflare, so at this point I just need to go to https://one.dash.cloudflare.com/ and then go to `Network > Tunnels`, click on the three dots on the right and select configure from the dropdown. Then you need to click the button on the bottom of the page to refresh you token. **Make sure to click the save button after you refresh the token** Then click on the docker command button and coppy the command. It should look like

```bash
docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token <tokenID>
```
We are going to go into Portainer to make this and not run it in the terminal. So log into Portainer and create a new container. Give it the name `cloudflareTunnel` (but it could be anything) and then in the image section paste
```
cloudflare/cloudflared:latest
```
Then scroll down to the Advanced Container Settings and then in the _Command_ section, select _Override_ and paste in the following command
```bash
tunnel --no-autoupdate run --token <tokenID>
```
Then click _Restart Policy_ and select _Always_. Finally click _Deploy the container_

You should then check the Cloudflare site make sure that the tunnel is healthy.


### 4. Install Nextcloud-aio
