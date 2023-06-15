import pkg_resources

packages = [
    'beautifulsoup4',
    'pandas',
    'requests',
    'tqdm'
]

for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f"{package}=={version}")
    except pkg_resources.DistributionNotFound:
        print(f"{package} is not installed")
