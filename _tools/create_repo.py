#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import stat
import md5
import re
import zipfile
import shutil
import urllib2
import json
import argparse
from xml.dom import minidom
from ConfigParser import SafeConfigParser


class main:
    def __init__(self, py_ver):
        self.py_ver = py_ver
        self.config = SafeConfigParser()
        self.config.read("config.ini")
        self.tools_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
        self.output_path = "pages/repo/"

        # travel path one up
        self.path_ad = os.path.abspath(os.path.join(self.tools_path, os.pardir))
        os.chdir(self.path_ad)

        # generate files
        self._pre_run()
        self._generate_addon_files()
        self._generate_repo_files()
        self._generate_md5_file()
        self._generate_zip_files()
        # notify user
        print "Finished updating addons xml, md5 files and zipping addons"

    def _pre_run(self):
        # create output  path if it does not exists
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def _generate_addon_files(self):
        if self.py_ver == 3:
            repo_urls = self.config.items("addons_py3")
        else:
            repo_urls = self.config.items("addons")
        if len(repo_urls) == 0:
            print "No addons in config.ini"
        else:
            for repo_url in repo_urls:
                self._get_release(repo_url[0], repo_url[1])
                shutil.rmtree('_temp')

    def _get_release(self, name, url):
        match = re.match('((?:[A-Za-z0-9+.-]+://)?.*?)(?:#([^#]*?))?(?::([^:]*))?$', url)
        (clone_repo, release_version, clone_path_option) = match.group(1, 2, 3)
        temp_path = '_temp/'
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        req = urllib2.Request("https://api.github.com/repos/{0}/releases/{1}".format(clone_repo, release_version))
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.21 Safari/537.36')
        req.add_header('Authorization', 'token {0}'.format(os.environ.get('GITHUB_TOKEN')))
        infostring = urllib2.urlopen(req).read()
        infostring = json.loads(infostring.decode('utf-8', 'replace'))
        print('Get {1} asserts for {0}'.format(name, release_version))
        for file in infostring['assets']:
            self.download_binary(file['browser_download_url'], temp_path+name+'.zip')
            zip = zipfile.ZipFile(temp_path+name+'.zip')
            zip.extractall(self.path_ad)
            zip.close()
            git_folder_path = os.path.abspath(os.path.join(self.path_ad, name, ".git"))
            if os.path.exists(git_folder_path):
                shutil.rmtree(git_folder_path)

    def download_binary(self, url, path):
        filedata = urllib2.urlopen(url)
        with open(path, 'wb') as f:
            f.write(filedata.read())

    def _generate_repo_files(self):
        # addon list
        addons = os.listdir( "." )
        addons.remove('.git')
        addons.remove('_tools')
        addons.remove('.gitignore')
        addons.remove('.travis.yml')
        addons.remove('pages')
        addons.remove('_py2')
        addons.remove('_py3')
        # final addons text
        addons_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n"
        # loop thru and add each addons addon.xml file
        for addon in addons:
            # create path
            _path = os.path.join( addon, "addon.xml" )
            #skip path if it has no addon.xml
            if not os.path.isfile( _path ): continue
            try:               
                # split lines for stripping
                xml_lines = open( _path, "r" ).read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if line.find( "<?xml" ) >= 0: continue
                    if self.py_ver == 3:
                        line = line.replace("%VERSION%", "~matrix").replace("%PY_VER%", "_matrix")
                    else:
                        line = line.replace("%VERSION%", "").replace("%PY_VER%", "")
                    if self.py_ver == 3 and line.find('"xbmc.python"') >= 0:
                        line = '        <import addon="xbmc.python" version="3.0.0"/>'
                    # add line
                    addon_xml += unicode( line.rstrip() + "\n", "utf-8" )
                # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception, e:
                # missing or poorly formatted addon.xml
                print "Excluding %s for %s" % ( _path, e, )
        if self.py_ver == 2:
            addons_xml += self._add_repo_py3().decode("utf-8").strip()
        # clean and add closing tag
        addons_xml = addons_xml.strip() + u"\n</addons>\n"
        # save file
        filename = "addons"
        if self.py_ver == 3:
            filename += "_matrix"
        self._save_file( addons_xml.encode( "utf-8" ), file=self.output_path + filename +".xml" )

    def _add_repo_py3(self):
        return """
<addon id="repository.nemiroff" version="1.0.2~matrix" name="Nemiroff Repository" provider-name="Nemiroff">
  <requires>
    <import addon="xbmc.python" version="3.0.0"/>
  </requires>
  <extension point="xbmc.addon.metadata">
    <summary lang="en">Nemiroff Repository</summary>
    <summary lang="ru">Репозиторий Nemiroff.</summary>
    <description lang="en">Addon repository by Nemiroff</description>
    <description lang="ru">Репозиторий дополнений Nemiroff</description>
    <platform>all</platform>
    <assets>
      <icon>icon.png</icon>
    </assets>
  </extension>
  <extension point="xbmc.addon.repository" name="nemiroff repository">
    <info compressed="false">https://nemiroff.github.io/kodi_repo/repo/addons_matrix.xml</info>
    <checksum>https://nemiroff.github.io/kodi_repo/repo/addons_matrix.xml.md5</checksum>
    <datadir zip="true">https://nemiroff.github.io/kodi_repo/repo</datadir>
  </extension>
</addon>
"""

    def _save_file(self, data, file):
        try:
            # write data to the file
            open( file, "w" ).write( data )
        except Exception, e:
            # oops
            print "An error occurred saving %s file!\n%s" % ( file, e, )

    def _generate_md5_file(self):
        try:
            # create a new md5 hash
            name = "addons"
            if self.py_ver == 3:
                name += "_matrix"
            m = md5.new( open(self.output_path + name + ".xml" ).read() ).hexdigest()
            # save file
            self._save_file( m, file=self.output_path + name + ".xml.md5" )
        except Exception, e:
            # oops
            print "An error occurred creating addons.xml.md5 file!\n%s" % ( e, )

    def _generate_zip_files(self):
        addons = os.listdir( "." )
        addons.remove('.git')
        addons.remove('_tools')
        addons.remove('.gitignore')
        addons.remove('.travis.yml')
        addons.remove('pages')
        addons.remove('_py2')
        addons.remove('_py3')
        # loop thru and add each addons addon.xml file
        for addon in addons:
            # create path
            _path = os.path.join(addon, "addon.xml")
            #skip path if it has no addon.xml
            if not os.path.isfile(_path): continue
            try:
                # skip any file or .git folder
                if (not os.path.isdir(addon) or addon == ".git" or addon == self.output_path or addon == self.tools_path): continue
                # create path
                _path = os.path.join(addon, "addon.xml")
                # split lines for stripping
                document = minidom.parse(_path)
                for parent in document.getElementsByTagName("addon"):
                    if self.py_ver == 3:
                        version = parent.getAttribute("version").replace("%VERSION%", "~matrix")
                    else:
                        version = parent.getAttribute("version").replace("%VERSION%", "")
                    addonid = parent.getAttribute("id")
                self._generate_zip_file(addon, version, addonid)
            except Exception, e:
                print e

    def _generate_zip_file(self, path, version, addonid):
        print "Generate zip file for " + addonid + "-" + version
        filename = path + "-" + version + ".zip"
        try:
            zip = zipfile.ZipFile(filename, 'w')
            for root, dirs, files in os.walk(path + os.path.sep):
                for file in files:
                    if file == "addon.xml":
                        addonxml = self.fix_addon_ver(os.path.join(root, file), version)
                        zip.writestr(os.path.join(root, 'addon.xml'), addonxml)
                    else:
                        zip.write(os.path.join(root, file))
            zip.close()

            if not os.path.exists(self.output_path + addonid):
                os.makedirs(self.output_path + addonid)
            if os.path.isfile(self.output_path + addonid + os.path.sep + filename):
                os.remove(self.output_path + addonid + os.path.sep + filename)
            shutil.move(filename, self.output_path + addonid + os.path.sep + filename)
            shutil.copy(path + os.path.sep + 'icon.png', self.output_path + addonid + os.path.sep + 'icon.png')
            shutil.copy(path + os.path.sep + 'fanart.jpg', self.output_path + addonid + os.path.sep + 'fanart.jpg')
            shutil.copy(path + os.path.sep + 'changelog.txt', self.output_path + addonid + os.path.sep + 'changelog.txt')
            shutil.copy(path + os.path.sep + 'changelog.txt', self.output_path + addonid + os.path.sep + 'changelog-' + version + '.txt')
        except Exception, e:
            print e

    def del_rw(action, name, exc):
        os.chmod(name, stat.S_IWRITE)
        os.remove(name)

    def fix_addon_ver(self, path, version):
        addon_xml = ""
        try:
            xml_lines = open( path, "r" ).read().splitlines()
            for line in xml_lines:
                if self.py_ver == 3:
                    line = line.replace("%VERSION%", "~matrix").replace("%PY_VER%", "_matrix")
                else:
                    line = line.replace("%VERSION%", "").replace("%PY_VER%", "")
                if line.find('"xbmc.python"') >= 0 and self.py_ver == 3:
                    line = '        <import addon="xbmc.python" version="3.0.0"/>'
                addon_xml += unicode( line.rstrip() + "\n", "utf-8" )
        except Exception, e:
            addon_xml = ""
            print "Excluding fix %s for %s" % ( path, e, )
        return addon_xml.encode('utf-8')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('py_ver', metavar='int', type=int, choices=[2,3], help="Py version addon")
    args = parser.parse_args()
    main(args.py_ver)
