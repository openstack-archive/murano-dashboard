function prepare_packages() {

    sudo wget https://sourceforge.net/projects/ubuntuzilla/files/mozilla/apt/pool/main/f/firefox-mozilla-build/firefox-mozilla-build_46.0.1-0ubuntu1_amd64.deb/download -O firefox46.deb
    sudo dpkg -i firefox46.deb
    sudo rm -f firefox46.deb

    sudo apt-get update
    sudo apt-get install -y \
      libpq-dev \
      python-dev \
      libxml2-dev \
      libxslt1-dev \
      libffi-dev \
      make \
      gcc \
      ntpdate \
      xvfb \
      zip \
      python-openssl \
      python-crypto  \
      libgtk-3-0 \
      libasound2 \
      libdbus-glib-1-2
}
