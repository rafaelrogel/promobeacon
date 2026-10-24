with open('firmware/main/web_server.c', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");\r\n    httpd_resp_set_hdr(req, "Cache-Control"'
rep = 'httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");\r\n    httpd_resp_set_hdr(req, "Connection", "close");\r\n    httpd_resp_set_hdr(req, "Cache-Control"'

if target in c:
    c = c.replace(target, rep)
else:
    target_lf = 'httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");\n    httpd_resp_set_hdr(req, "Cache-Control"'
    rep_lf = 'httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");\n    httpd_resp_set_hdr(req, "Connection", "close");\n    httpd_resp_set_hdr(req, "Cache-Control"'
    c = c.replace(target_lf, rep_lf)

with open('firmware/main/web_server.c', 'w', encoding='utf-8', newline='') as f:
    f.write(c)

print('Updated probe handler with Connection: close!')
