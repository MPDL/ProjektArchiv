var axios = require('axios');
var FormData = require('form-data');

class KeeperAPI {

  init({ server, username, password, token }) {
    this.server = server;
    this.username = username;
    this.password = password;
    this.token = token;  //none
    if (this.token && this.server) {
      this.req = axios.create({
        baseURL: this.server,
        headers: { 'Authorization': 'Token ' + this.token }
      });
    }
    return this;
  }

  initForSeahubUsage({ siteRoot, xcsrfHeaders }) {
    if (siteRoot && siteRoot.charAt(siteRoot.length - 1) === "/") {
      var server = siteRoot.substring(0, siteRoot.length - 1);
      this.server = server;
    } else {
      this.server = siteRoot;
    }

    this.req = axios.create({
      headers: {
        'X-CSRFToken': xcsrfHeaders,
      }
    });
    return this;
  }

  _sendPostRequest(url, form) {
    if (form.getHeaders) {
      return this.req.post(url, form, {
        headers: form.getHeaders()
      });
    } else {
      return this.req.post(url, form);
    }
  }

  getToken() {
    const url = this.server + '/api2/auth-token/';
    axios.post(url, {
      username: this.username,
      password: this.password
    }).then((response) => {
      this.token = response.data;
      return this.token;
    })
  }

  certifyOnBloxberg(repoID, path) {
    const url = this.server + '/api2/certify/';
    const params = {
      repo_id: repoID,
      path: path
    }
    return this.req.post(url, params);
  }

  addDoi(repoID) {
    const url = this.server + '/api2/doi/';
    const params = {
      repo_id: repoID
    }
    return this.req.post(url, params);
  }

  canArchive(repoID) {
    const url = this.server + '/api2/can-archive/';
    const params = {
      repo_id: repoID
    }
    return this.req.post(url, params);
  }

   archiveLibrary(repoID) {
    const url = this.server + '/api2/archive/';
    const params = {
      repo_id: repoID
    }
    return this.req.post(url, params);
  }

  listLibraryDetails() {
    const url = this.server + '/api2/library-details/';
    return this.req.get(url);
  }

}

export { KeeperAPI };