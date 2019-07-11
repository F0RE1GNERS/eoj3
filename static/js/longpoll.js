function longPoll(url, callback, restInterval, stopCondition, timeout) {
  // when stopCondition(something) is true, callback will be called and no more poll request
  $.ajax({
    url: url,
    dataType: "json",
    success: function (data) {
      if (stopCondition(data)) {
        callback(data);
      } else {
        setTimeout(function () {
          longPoll(url, callback, restInterval, stopCondition, timeout);
        }, restInterval);
      }
    },
    timeout: timeout || 30000
  });
}

function longPollUntilForever(url, callback, restInterval, timeout) {
  $.ajax({
    url: url,
    success: callback,
    dataType: "json",
    complete: function () {
      setTimeout(function () {
        longPollUntilForever(url, callback, restInterval, timeout);
      }, restInterval);
    },
    timeout: timeout || 30000
  });
}