# S3 Preloader
Intended for use as an init container when your workload needs some files, but you want those
files to come from S3. 

# Usage
Add this image to an initContainer in the pod.
Add a volume to your pod. It can be of any type, including emptyDir
Mount the volume into this container at the path /mnt/download_here
Mount the same volume into your workload wherever needed.
Provide AWS credentials/config by mounting to /home/.aws (likely from a kubernetes secret)
Configure this downloader with max number of files, etc with env vars