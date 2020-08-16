$( function() {

  $.support.cors = true
  var apiurl = "https://openlibrary.org";

  requests = {
    get: function(url, callback) {
      $.get(url, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    post: function(url, data, callback) {
      $.post(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },

    put: function(url, data, callback) {
      $.put(url, data, function(results) {
      }).done(function(data) {
        if (callback) { callback(data); }
      });
    },
  };

  var bind_autocomplete = function(self, selector) {
    $(selector).autocomplete({
      source: function (request, response) {
        $.ajax({
          url: apiurl + '/search.json?limit=10&q=' + request.term,
          success: function(resp) {
            var entities = $.map(resp.docs, function(book) {              
              return {
                label: book.title,
                value: book.id,
                img: 'https://covers.openlibrary.org/b/olid/' + book.cover_edition_key + '-S.jpg'
              }
            });
            response(entities);
          }
        });
      },
      minLength: 2,
      focus: function (event, ui) {
        $(event.target).val(ui.item.label);
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);
        return false;
      },
      select: function (event, ui) {
        $(selector).val(ui.item.label);
        $(selector).attr('eid', ui.item.value);
        return false;
      }
    }).data("ui-autocomplete")._renderItem = function (ul, item) {
      return $("<li />")
        .data( "ui-autocomplete-item", item)
        .append("<a class='book-result'><img src='" + item.img + "' />" + item.label + "</a>")
        .appendTo(ul);
    };
  }

  bind_autocomplete(self, ".book-winner-selector");
  bind_autocomplete(self, ".book-candidate-selector");
});