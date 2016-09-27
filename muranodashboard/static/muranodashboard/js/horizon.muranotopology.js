/**
 * Adapted for Murano js topology generator.
 * Based on:
 * HeatTop JS Framework
 * Dependencies: jQuery 1.7.1 or later, d3 v3 or later
 * Date: June 2013
 * Description: JS Framework that subclasses the D3 Force Directed Graph library to create
 * Heat-specific objects and relationships with the purpose of displaying
 * Stacks, Resources, and related Properties in a Resource Topology Graph.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

$(function() {
  "use strict";
  horizon.tabs._init_load_functions.push(loadMuranoTopology);

  function loadMuranoTopology() {
    var muranoContainer = "#murano_application_topology";
    if ($(muranoContainer).length === 0) {
      return;
    }

    /**
     * var diagonal = d3.svg.diagonal()
     *   .projection(function(d) { return [d.y, d.x]; });
     */

    /**
     * If d3 is undefined, and give an assignment
     * It solves no-def error: d3 is not defined
     */
    //var d3 = d3 || {};

    /**
     * Declare global variables
     */
    var ajaxUrl,
      force,
      node,
      link,
      needsUpdate,
      nodes,
      links,
      inProgress;

    function update() {
      node = node.data(nodes, function(d) {
        return d.id;
      });
      link = link.data(links);

      var nodeEnter = node.enter().append("g")
        .attr("class", "node")
        .attr("node_name", function(d) {
          return d.name;
        })
        .attr("node_id", function(d) {
          return d.id;
        })
        .call(force.drag);

      nodeEnter.append("image")
        .attr("xlink:href", function(d) {
          return d.image;
        })
        .attr("id", function(d) {
          return "image_" + d.id;
        })
        .attr("x", function(d) {
          return d.image_x;
        })
        .attr("y", function(d) {
          return d.image_y;
        })
        .attr("width", function(d) {
          return d.image_size;
        })
        .attr("height", function(d) {
          return d.image_size;
        })
        .attr("clip-path", "url(#clipCircle)");
      node.exit().remove();

      link.enter().insert("path", "g.node")
        .attr("class", function(d) {
          return "link " + d.link_type;
        });

      link.exit().remove();
      //Setup click action for all nodes
      node.on("mouseover", function(d) {
        $("#info_box").html(d.info_box);
        //current_info = d.name;
      });
      node.on("mouseout", function() {
        $("#info_box").html('');
      });

      force.start();
    }

    function drawLink(d) {
      return "M" + d.source.x + "," + d.source.y + "L" + d.target.x + "," + d.target.y;
    }

    function tick() {
      link.attr('d', drawLink).style('stroke-width', 3).attr('marker-end', "url(#end)");
      node.attr("transform", function(d) {
        return "translate(" + d.x + "," + d.y + ")";
      });
    }

    function setInProgress(stack, innerNodes) {
      if (stack.in_progress === true) {
        inProgress = true;
      }
      for (var i = 0; i < innerNodes.length; i++) {
        var d = innerNodes[i];
        if (d.in_progress === true) {
          inProgress = true; return false;
        }
      }
    }

    function findNode(id) {
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) {
          return nodes[i];
        }
      }
    }

    function findNodeIndex(id) {
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === id) {
          return i;
        }
      }
    }

    function addNode(innerNode) {
      nodes.push(innerNode);
      needsUpdate = true;
    }

    function removeNode(id) {
      var i = 0;
      var n = findNode(id);
      while (i < links.length) {
        if (links[i].source === n || links[i].target === n) {
          links.splice(i, 1);
        } else {
          i++;
        }
      }
      nodes.splice(findNodeIndex(id), 1);
      needsUpdate = true;
    }

    function removeNodes(oldNodes, newNodes) {
      //Check for removed nodes
      for (var i = 0; i < oldNodes.length; i++) {
        var isRemoveNode = true;
        for (var j = 0; j < newNodes.length; j++) {
          if (oldNodes[i].id === newNodes[j].id) {
            isRemoveNode = false;
            break;
          }
        }
        if (isRemoveNode === true) {
          removeNode(oldNodes[i].id);
        }
      }
    }

    function buildNodeLinks(innerNode) {
      for (var j = 0; j < innerNode.required_by.length; j++) {
        var pushLink = true;
        var targetIdx = '';
        var sourceIdx = findNodeIndex(innerNode.id);
        //make sure target node exists
        try {
          targetIdx = findNodeIndex(innerNode.required_by[j]);
        } catch (err) {
          if (window.console) {
            window.console.log(err);
          }
          pushLink = false;
        }
        //check for duplicates
        for (var lidx = 0; lidx < links.length; lidx++) {
          if (links[lidx].source === sourceIdx && links[lidx].target === targetIdx) {
            pushLink = false;
            break;
          }
        }

        if (pushLink === true && (sourceIdx && targetIdx)) {
          links.push({
            "target": sourceIdx,
            "source": targetIdx,
            "value": 1,
            "link_type": innerNode.link_type
          });
        }
      }
    }

    function buildReverseLinks(innerNode) {
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].required_by) {
          for (var j = 0; j < nodes[i].required_by.length; j++) {
            var dependency = nodes[i].required_by[j];
            //if new node is required by existing node, push new link
            if (innerNode.id === dependency) {
              links.push({
                "target": findNodeIndex(nodes[i].id),
                "source": findNodeIndex(innerNode.id),
                "value": 1,
                "link_type": nodes[i].link_type
              });
            }
          }
        }
      }
    }

    function buildLinks() {
      for (var i = 0; i < nodes.length; i++) {
        buildNodeLinks(nodes[i]);
        buildReverseLinks(nodes[i]);
      }
    }

    function ajaxPoll(pollTime) {
      setTimeout(function() {
        $.getJSON(ajaxUrl, function(json) {
          //update d3 data element
          $("#d3_data").attr("data-d3_data", JSON.stringify(json));

          //update stack
          $("#stack_box").html(json.environment.info_box);
          setInProgress(json.environment, json.nodes);
          needsUpdate = false;

          //Check Remove nodes
          removeNodes(nodes, json.nodes);

          //Check for updates and new nodes
          json.nodes.forEach(function(d) {
            var currentNode = findNode(d.id);
            //Check if node already exists
            if (currentNode) {
              //Node already exists, just update it
              currentNode.status = d.status;

              //Status has changed, image should be updated
              if (currentNode.image !== d.image) {
                currentNode.image = d.image;
                var thisImage = d3.select("#image_" + currentNode.id);
                thisImage
                  .transition()
                  .attr("x", function(dImage) {
                    return dImage.image_x + 5;
                  })
                  .duration(100)
                  .transition()
                  .attr("x", function(dImage) {
                    return dImage.image_x - 5;
                  })
                  .duration(100)
                  .transition()
                  .attr("x", function(dImage) {
                    return dImage.image_x + 5;
                  })
                  .duration(100)
                  .transition()
                  .attr("x", function(dImage) {
                    return dImage.image_x - 5;
                  })
                  .duration(100)
                  .transition()
                  .attr("xlink:href", d.image)
                  .transition()
                  .attr("x", function(dImage) {
                    return dImage.image_x;
                  })
                  .duration(100)
                  .ease("bounce");
              }

              //Status has changed, update info_box
              currentNode.info_box = d.info_box;

            } else {
              addNode(d);
              buildLinks();
            }
          });

          //if any updates needed, do update now
          if (needsUpdate === true) {
            update();
          }
        });
        //if no nodes still in progress, slow AJAX polling
        if (inProgress === false) {
          pollTime = 30000;
        } else {
          pollTime = 3000;
        }
        ajaxPoll(pollTime);
      }, pollTime);
    }

    if ($(muranoContainer).length) {
      var width = $(muranoContainer).width();
      var height = 1040;
      var environmentId = $("#environment_id").data("environment_id");
      var graph = $("#d3_data").data("d3_data");
      var svg = d3.select(muranoContainer).append("svg")
        .attr("width", width)
        .attr("height", height);

      ajaxUrl = '/app-catalog/' + environmentId + '/services/get_d3_data';
      force = d3.layout.force()
        .nodes(graph.nodes)
        .links([])
        .gravity(0.25)
        .charge(-3000)
        .linkDistance(100)
        .size([width, height])
        .on("tick", tick);
      node = svg.selectAll(".node");
      link = svg.selectAll(".link");
      needsUpdate = false;
      nodes = force.nodes();
      links = force.links();
      svg.append("svg:clipPath")
        .attr("id", "clipCircle")
        .append("svg:circle")
        .attr("cursor", "pointer")
        .attr("r", "38px");

      svg.append("svg:defs").selectAll("marker")
        .data(["end"])      // Different link/path types can be defined here
        .enter().append("svg:marker")    // This section adds in the arrows
        .attr("id", String)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 25)
        .attr("refY", 0)
        .attr("fill", "#999")
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("svg:path")
        .attr("d", "M0,-3L10,0L0,3");

      buildLinks();
      update();

      //Load initial Stack box
      $("#stack_box").html(graph.environment.info_box);
      //On Page load, set Action In Progress
      inProgress = false;
      setInProgress(graph.environment, node);

      //If status is In Progress, start AJAX polling
      var pollTime = 0;
      if (inProgress === true) {
        pollTime = 3000;
      } else {
        pollTime = 30000;
      }
      ajaxPoll(pollTime);
    }
  }
});
