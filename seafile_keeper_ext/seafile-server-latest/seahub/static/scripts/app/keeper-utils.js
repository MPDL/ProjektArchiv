define([
  'jquery',
  'underscore',
  'common',
  'js.cookie'
], function ($, _, Common, Cookie) {
  'use strict';

  var keeperUtils = {}


  keeperUtils.start_archive = function (repo_name, repo_id) {
    $.ajax({
      url: "/api2/ajax/can-archive/",
      data: {
        repo_id: repo_id,
      },
      cache: false,
      dataType: 'json',
      success: function (data) {
        if (data.status === "success") {
          keeperUtils.archive(repo_name, repo_id, data.quota);
        } else if (data.status === "oversized") {
          keeperUtils.archive_failed(repo_name, "oversized");
        } else if (data.status === "quota_expired") {
          keeperUtils.archive_failed(repo_name, "quota_expired");
        } else if (data.status === "metadata_error") {
          keeperUtils.archive_failed(repo_name, "metadata_error", data.msg);
        }
      },
      error: function (error) {
        keeperUtils.archive_failed(repo_name, "unknown");
      }
    })
    return false;
  }


  keeperUtils.archive = function (repo_name, repo_id, quota) {
    var archive_info = "By archiving this library, the current state of everything contained within it will be archived on a dedicated archiving system. For more information, please follow the link: >TBC (will go to help center)<. This library can be archived " + quota + " more times.";
    var $form = $('<form action="" method=""><h3 id="dialogTitle">Archive <span style="color:#57a5b8;">' + repo_name + '</span></h3><p>' + archive_info + '</p><button type="submit" class="submit">Archive</button></form>');

    var $el = $('<div><span class="loading-icon loading-tip"></span></div>');
    $el.modal({ focus: false, minWidth: 400 });
    $('#simplemodal-container').css({ 'height': 'auto' });
    $('#simplemodal-data').html($form);

    $form.on('submit', function () {
      var $submit = $('[type="submit"]', $form);

      Common.disableButton($submit);
      $.ajax({
        url: "/api2/ajax/archive/",
        data: {
          repo_id: repo_id,
        },
        dataType: "json",
        beforeSend: Common.prepareCSRFToken,
        success: function (data) {
          if (data.status) {
            Common.feedback(data.msg, data.status, 8000);
          } else {
            Common.ajaxErrorHandler('Archive Library Failed');
          }
        }
      });
      $.modal.close();
      return false;
    });
  }


  keeperUtils.archive_failed = function (repo_name, error_type, error_msg = "") {
    var archive_info;
    switch (error_type) {
      case "quota_expired":
        archive_info = "Can not archive due to quota expired, please contact support.";
        break;
      case "metadata_error":
        archive_info = error_msg;
        break;
      case "oversized":
        archive_info = "Archive is only available for Libraries under 500G.";
        break;
      default:
        archive_info = "Can not archive due to unknown reason, please contact support.";
        break;
    }

    var $form = $('<form action="" method=""><h3 id="dialogTitle">Archive <span style="color:#57a5b8;">' + repo_name + '</span></h3><p>' + archive_info + '</p><');
    var $el = $('<div><span class="loading-icon loading-tip"></span></div>');
    $el.modal({ focus: false, minWidth: 400 });
    $('#simplemodal-container').css({ 'height': 'auto' });
    $('#simplemodal-data').html($form);
  }

  return keeperUtils;
});