#-*- coding: utf-8 -*-
"""
@file
@brief An example of a custom magic for IPython.
"""
import sys, os

from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.core.magic import line_cell_magic
from IPython.core.display import HTML                                
from .remote_connection import ASSHClient

@magics_class
class MagicRemote(Magics):
    """
    Defines commands to access a remote machine (bridge) through SSH,
    for the time being, all the command do not accept another parameters
    such as a SSH client which means only one connection
    can be opened at the same time.
    """
    
    def get_connection(self):
        """
        returns the connection stored in the workspace
        """
        if self.shell is None:
            raise Exception("No detected workspace.")
            
        if "remote_ssh" not in self.shell.user_ns:
            raise KeyError("No opened SSH connection.")
            
        return self.shell.user_ns["remote_ssh"]
        
    @cell_magic
    def PIG(self, line, cell = None):
        """
        defines command ``%%PIG``
        """
        if line in [None, ""] :
            print("Usage:")
            print("     %%PIG <filename>")
            print("")
            print("The command store the content of the cell as a local file.")
        else:
            filename = line.strip()
            with open(filename, "w", encoding="utf8") as f :
                f.write(cell.replace("\r",""))
            
    @line_magic
    def jobsubmit(self, line):
        """
        defines command ``%jobsubmit``
        """
        if line in [None, ""]:
            print("Usage:")
            print("  %jobsubmit <jobname.pig> [redirection]")
            print("")
            print("If redirection is specified, the standard output and error are redirected to")
            print("redirection.out, redirection.err and the function does not wait.")
        else:
            filename = line.strip()
            spl = filename.split()
            filename = spl[0]
            redirection = None if len(spl) == 1 else spl[1]
            if not os.path.exists(filename):
                raise FileNotFoundError(filename)
                
            dest = os.path.split(filename)[-1]
            ssh = self.get_connection()
            ssh.upload(filename, dest)
            
            if redirection is None:
                cmd = "pig -execute -f " + dest
            else:
                cmd = "pig -execute -f {0} 2> {1}.err 1> {1}.out &".format(filename, redirection)
            
            out, err = ssh.execute_command(cmd, no_exception = True)
            if len(err) > 0 and (len(out) == 0 or "ERROR" in err or "FATAL" in err or "Exception" in err):
                return HTML("<pre>\n%s\n</pre>" % err)
            else:
                return HTML("<pre>\n%s\n</pre>" % out)
    
    @line_magic
    def jobsyntax(self, line):
        """
        defines command ``%jobsyntax``
        """
        if line in [None, ""]:
            print("Usage:")
            print("  %jobsyntax <jobname.pig>")
            print("")
        else:
            filename = line.strip()
            if not os.path.exists(filename):
                raise FileNotFoundError(filename)
                
            dest = os.path.split(filename)[-1]
            ssh = self.get_connection()
            ssh.upload(filename, dest)
            out, err = ssh.execute_command("pig -check " + dest, no_exception = True)
            if len(err) > 0 and (len(out) == 0 or "ERROR" in err or "FATAL" in err or "Exception" in err):
                return HTML("<pre>\n%s\n</pre>" % err)
            else:
                return HTML("<pre>\n%s\n</pre>" % out)
    
    @line_magic
    def remote_open (self, line):
        """
        open a SSH connection and store the connection
        into the notebook workspace
        """
        spl = line.strip().split()
        if len(spl) != 3 and len(spl) != 0:
            print("Usage:")
            print("   remote_open <server> <username> <password>")
            print("   remote_open")
            print("")
            print("No parameter means server, username, password will be found in the workspace")
        else:
            if len(spl)==3:
                server,username,password = spl
            elif self.shell is not None:
                server   = self.shell.user_ns.get("server",None)
                username = self.shell.user_ns.get("username",None)
                password = self.shell.user_ns.get("password",None)
                if server is None : raise KeyError("unable to find server")
                if username is None : raise KeyError("unable to find username")
                if password is None : raise KeyError("unable to find password")
            else:
                raise Exception("No detected workspace.")
                
            if self.shell is None:
                raise Exception("No detected workspace.")
                
            ssh = ASSHClient(server, username, password)
            ssh.connect()
            
            self.shell.user_ns["remote_ssh"] = ssh
            return ssh
            
    @line_magic
    def remote_close (self, line):
        """
        close a SSH connection and store the connection
        into the notebook workspace
        """
        self.get_connection().close()
        
    @line_magic
    def remote_cmd(self, line):
        """
        run a command on the remote machine
        
        Example::
        
            %remote_cmd ls
        """
        ssh = self.get_connection()
        ssh = self.shell.user_ns["remote_ssh"]
        out, err = ssh.execute_command(line, no_exception = True)
        if len(err) > 0 and (len(out) == 0 or "ERROR" in err or "FATAL" in err or "Exception" in err):
            return HTML("<pre>\n%s\n</pre>" % err)
        else:
            return HTML("<pre>\n%s\n</pre>" % out)
    
    @line_magic
    def remote_up(self, line):
        """
        upload a file to the remote machine,
        
        Example::
        
            %remote_up localfile remotepath
            
        the command does not allow spaces in files
        """
        spl = line.strip().split()
        if len(spl) != 2 :
            print("Usage:")
            print("   remote_up <localfile> <remotepath>")
            print("")
            print("no space allow in file names")
        else :
            ssh = self.get_connection()
            localfile,remotepath = spl
            if not os.path.exists(localfile) :
                raise FileNotFoundError(localfile)
            ssh.upload(localfile, remotepath)
            
    @line_magic
    def remote_down(self, line):
        """
        download a file from the remote machine,
        
        Example::
        
            %remote_down remotepath localfile
            
        the command does not allow spaces in files
        """
        spl = line.strip().split()
        if len(spl) != 2 :
            print("Usage:")
            print("   remote_up <localfile> <remotepath>")
            print("")
            print("no space allow in file names")
        else :
            ssh = self.get_connection()
            remotepath,localfile = spl
            if os.path.exists(localfile) :
                raise Exception("file {0} cannot be overwritten".format(localfile))
            ssh.download(remotepath,localfile)

def register_magics():
    """
    register magics function, can be called from a notebook
    """
    ip = get_ipython()
    ip.register_magics(MagicRemote)
    