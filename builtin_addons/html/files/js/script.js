function make_command_html_listing(command_object) {
    const template = document.querySelector("#template_command_details");
    const clone = template.content.cloneNode(true);
    clone.querySelector(".command_details_name").textContent = command_object.command_name;
    for (let v in command_object.variables) {
        clone.querySelector(".command_details_variables").appendChild(make_variable_html_listing(v, command_object.variables[v]));
    }
    return clone;
}
function make_procedure_html_listing(proc_name, proc_array) {
    const template = document.querySelector("#template_procedure_details");
    const clone = template.content.cloneNode(true);
    clone.querySelector(".procedure_details_name").textContent = proc_name;
    let command_container = clone.querySelector(".procedure_details_commands");
    for (let com of proc_array) {
        let newnode = make_command_html_listing(com);
        if (command_container.childElementCount % 2 == 1) {
            newnode.querySelector(".command_details").classList.add("list_odd_item");
        }
        command_container.appendChild(newnode);
    }
    return clone;
}
function make_variable_html_listing(variable_name, variable_object) {
    const template = document.querySelector("#template_variable_details");
    const clone = template.content.cloneNode(true);
    clone.querySelector(".variable_details_name").textContent = variable_name;
    clone.querySelector(".variable_details_typename").textContent = variable_object.typename;
    clone.querySelector(".variable_details_value").textContent = variable_object.value;
    return clone;
}
function make_workflow_total_html_listing(workflow) {
    const template = document.querySelector("#template_workflow_details");
    const clone = template.content.cloneNode(true);
    clone.querySelector(".workflow_details").id = workflow.name;
    clone.querySelector(".workflow_details_name").textContent = workflow.name;
    clone.querySelector(".workflow_details_state").textContent = workflow.state;
    clone.querySelector(".workflow_details_user_notes").textContent = workflow.user_notes;

    for (let v in workflow.constants) {
        clone.querySelector(".workflow_details_constants").appendChild(make_variable_html_listing(v, workflow.constants[v]));
    }
    for (let v in workflow.setup_variables) {
        clone.querySelector(".workflow_details_setup_variables").appendChild(make_variable_html_listing(v, workflow.setup_variables[v]));
    }
    for (let v in workflow.procedures) {
        clone.querySelector(".workflow_details_procedures").appendChild(make_procedure_html_listing(v, workflow.procedures[v]));
    }
    return clone;
}
async function list_all_workflows() {
    const response = await fetch("/api/workflows");
    const workflows = await response.json();
    let container = document.getElementById("workflow_list");
    container.innerHTML = "";
    for (let w of workflows) {
        container.appendChild(make_workflow_total_html_listing(w));
    }
}
async function workflow_toggle_state(button) {
    let current_state = button.textContent;
    let workflow_node = button.parentNode;
    let name = workflow_node.querySelector(".workflow_details_name").textContent;

    let uri_path = "/api/workflows/" + name;
    if (current_state == "Running") {
        uri_path += "/pause";
    } else {
        uri_path += "/unpause";
    }
    fetch(uri_path, {
        method: "POST"
    }).then(refresh_total_page);
}


function make_instance_total_html_listing(instance) {
    const template = document.querySelector("#template_instance_details");
    const clone = template.content.cloneNode(true);
    clone.querySelector(".instance_details").id = instance.uuid;
    clone.querySelector(".instance_details_uuid").textContent = instance.uuid;
    clone.querySelector(".instance_details_workflow_name").textContent = instance.workflow_name;
    clone.querySelector(".instance_details_state").textContent = instance.state;
    clone.querySelector(".instance_details_process_name").textContent = instance.processing_step[0];
    clone.querySelector(".instance_details_process_step").textContent = instance.processing_step[1];
    clone.querySelector(".instance_details_next_processing_time").textContent = instance.next_processing_time;
    clone.querySelector(".instance_details_console_log").textContent = instance.console_log;
    clone.querySelector(".instance_details_console_log_display").innerHTML = instance.console_log.replace(/\n/g, "<br>");
    for (let v in instance.variables) {
        clone.querySelector(".instance_details_variables").appendChild(make_variable_html_listing(v, instance.variables[v]));
    }
    return clone;
}
async function list_all_instances() {
    const response = await fetch("/api/instances");
    const instance = await response.json();
    let orphan_container = document.getElementById("orphan_instance_list");
    orphan_container.innerHTML = "";
    for (let i of instance) {
        let inode = make_instance_total_html_listing(i);
        let wnode = undefined;
        try {
            wnode = document.getElementById(i.workflow_name);
        } catch (e) {
            console.error(e);
        }
        if (!wnode) {
            orphan_container.appendChild(inode);
        } else {
            wnode.getElementsByClassName("workflow_details_instances")[0].appendChild(inode);
        }
    }
}
async function instance_toggle_state(button) {
    let current_state = button.textContent;
    let instance_node = button.parentNode;
    let uuid = instance_node.querySelector(".instance_details_uuid").textContent;

    let uri_path = "/api/instances/" + uuid;
    if (current_state == "Running") {
        uri_path += "/pause";
    } else {
        uri_path += "/unpause";
    }
    fetch(uri_path, {
        method: "POST"
    }).then(refresh_total_page);
}


async function refresh_total_page() {
    await list_all_workflows();
    list_all_instances();
}


function collapsed_section_toggle(caller_node) {
    let section = caller_node.nextElementSibling;
    while (section) {
        if (section.classList.contains("collapsable")) {
            section.classList.remove("collapsable");
            section.classList.add("collapsable_disabled");
            return;
        }
        if (section.classList.contains("collapsable_disabled")) {
            section.classList.remove("collapsable_disabled");
            section.classList.add("collapsable");
            return;
        }
        section = section.nextElementSibling;
    }
}


window.addEventListener("load", () => {
    console.log("Load Setup");
    // for( let x of document.getElementsByClassName("collapse_button") ){
    //     console.log(x);
    //     x.addEventListener("click",collapsed_section_toggle.bind(x));
    // }
    refresh_total_page();
});