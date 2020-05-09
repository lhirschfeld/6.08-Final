const robots_list = document.getElementById('robots');
const queue_list = document.getElementById('queue');
const history_list = document.getElementById('history');
const robot_buttons = document.getElementsByClassName('robot-button');

let selected_robot = '';
let known_robots = new Set();
let running_robots = new Set();

const createNode = (element) => {
    return document.createElement(element);
}

const append = (parent, el) => {
    return parent.appendChild(el);
}

const build_card = (job) => {
    let li = createNode('li');
    li.innerHTML = `
        <div class='uk-card uk-card-default uk-card-body' uk-grid>
            <dl class='uk-description-list uk-width-1-2@l'>
                <dt>Unique ID</dt>
                <dd>${job.id}</dd>
                <dt>Timestamp</dt>
                <dd>${job.timestamp}</dd>
                <dt>Status</dt>
                <dd>${job.status}</dd>
                <dt>Robot</dt>
                <dd>${job.robot}</dd>
            </dl>
            <dl class='uk-description-list uk-width-1-2@l'>
                <dt>Container</dt>
                <dd>${job.container}</dd>
                <dt>Run Command</dt>
                <dd>${job.run_command}</dd>
                <dt>Mount</dt>
                <dd>${job.mount}/</dd>
            </dl>
            <ul class='uk-width-1-1' uk-accordion>
                <li>
                    <a class="uk-accordion-title" href="#">Logs</a>
                    <div class="uk-accordion-content">
                        <pre><code>${job.logs}</code></pre>
                    </div>
                </li>
            </ul>
        </div>`
    return li;
}

const build_robots = (robot, active) => {
    let running = running_robots.has(robot);
    let li = createNode('li');
    li.setAttribute('data-tags', active ? 'active' : running ? 'running' : 'stale');
    li.innerHTML = `
        <div class='uk-card uk-card-small uk-card-${robot === selected_robot ? 'secondary' : 'default'} uk-card-body robot-button'>
            ${robot}
            <br />
            <span class='uk-label uk-label-${active ? 'success' : running ? 'danger' : 'warning'}'>
                ${active ? 'Active' : running ? 'Running' : 'Inactive'}
            </span>
        </div>
    `

    li.onclick = () => {
        selected_robot = robot;
        fill_everything();
    }

    return li;
}

const fill_queue = (robot_name) => {
    fetch(`${API_HOST}/queue/${robot_name}`)
    .then((resp) => resp.json())
    .then(function(jobs) {
        queue_list.innerHTML = '';
        return jobs.map(function(job) {
            known_robots.add(job.robot);
            append(queue_list, build_card(job));
        });
    })
    .catch(function(error) {
        console.log('Error when pulling queue.');
        console.log(error);
    });
}

const fill_history = (robot_name) => {
    fetch(`${API_HOST}/history/${robot_name}`)
    .then((resp) => resp.json())
    .then(function(jobs) {
        history_list.innerHTML = '';
        running_robots = new Set();
        return jobs.map(function(job) {
            known_robots.add(job.robot);

            if (job.status === 'running') {
                running_robots.add(job.robot);
            }

            append(history_list, build_card(job));
        });
    })
    .catch(function(error) {
        console.log('Error when pulling history.');
        console.log(error);
    });
}

const fill_robots = () => {
    fetch(`${API_HOST}/activity/`)
    .then((resp) => resp.json())
    .then(function(active_robots) {
        active_robots.forEach((robot, _) => {
            known_robots.add(robot);
        });

        robots_list.innerHTML = '';
        
        let li = createNode('li');
        li.setAttribute('data-tags', 'active stale');
        li.innerHTML = `
            <div class='uk-card uk-card-small uk-card-primary uk-card-body robot-button'>All Robots</div>
        `
        li.onclick = () => {
            selected_robot = '';
            fill_everything();
        }

        append(robots_list, li);

        return [...known_robots].sort().map((robot) => {
            append(robots_list, build_robots(robot, active_robots.includes(robot)));
        });
    })
    .catch(function(error) {
        console.log('Error when pulling active robots.');
        console.log(error);
    });
}

const fill_everything = () => {
    fill_queue(selected_robot);
    fill_history(selected_robot);
    fill_robots();
}

// Regularly update.
window.setInterval(fill_everything, 1000*5);

// On initial load.
fill_everything();