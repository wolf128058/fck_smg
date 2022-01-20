# F*CK SMG

## Motivation

With the introduction of the GDPR we have a lot of funny inventions beeing sold as neccesary evils.
One of these are the so-called "SecureMail Gateways".

As a receiver from outside beeing forced to login somewhere on a webserver instead of having the actual mails in my mailbox is annoying to me.
Also automatically sent acknowledgements of receipt rather harm than protect my privacy.
There is only a little more transport security level, but no real security advantage for me, because mails on this servers are probably still unencrypted and readable for the operators of this servers.

So while managment tells us, that there is more security now, they are just enjoying the centralisation.
We all know:

 - There is no security by obscurity
 - Good message encryption works end-to-end
 - ["Bullshit made in Germany"](https://youtu.be/p56aVppK2W4) aka De-Mail failed.
 - The beA aka "Besonderes elektronisches Anwaltspostfach" [failed, too](https://youtu.be/I_tyTYAVYDo)

But my german diocese still does not know. And so they introduced another piece of centralised crypto-stuff, that has at least in my humble opinion some defective design.

## Solution
With this little tool, you can completely simulate a remote login on their gateway, download your inbox-messages there and save them in one of your own IMAP-Directories, so that you get the messages in your old-famliar mail-client. Possibly even without sending those acknowledgements of receipt. Just imagine using that as a cronjob. Or just use it as a cronjob.

## Warning!
**Storing passwords in plaintext is a very risky thing!**
But to get this tool running, you need to save the credentials for your Mail-Gateway and your IMAP-Server in the *.env*. So please never ever try this on file-storages where other people have access to and always transfer this file secure.

You are using this tool on your own risk.


## Used Sources
Thanks to Quentin Stafford-Fraser for the file *imapdedup.py*, which I found on [GitHub](https://github.com/quentinsf/IMAPdedup) under GPLv2.
IMAPdedup is great, because we do not want to mark the downloaded mails as read and do not want to have duplicates in the IMAP directory. Thats what IMAPdedup solves.
