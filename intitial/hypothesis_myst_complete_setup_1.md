# Hypothesis + MyST Documentation Setup Guide
## Complete Step-by-Step for Windows 11 + WSL + JFrog

---

## 📋 What You're Building

**Goal**: Host Hypothesis annotation server locally and integrate with your MyST documentation so you and colleagues can annotate docs together in real-time.

**Architecture**:
```
Windows 11
  └─ WSL (Ubuntu)
      ├─ Hypothesis Server (built from source)
      ├─ PostgreSQL (from JFrog proxy)
      ├─ Elasticsearch (from JFrog proxy)
      ├─ RabbitMQ (from JFrog proxy)
      └─ Your MyST Docs (served locally with Hypothesis embed)
```

---

## 🔧 Prerequisites Check

Open WSL terminal and verify:

```bash
# Check Docker
docker --version
docker ps

# Check Python
python3 --version

# Check Git
git --version

# Check you can access JFrog
docker login dfa.jfrog.io
# Enter your credentials when prompted
```

---

## 📦 Part 1: Clone and Build Hypothesis

### Step 1.1: Clone the Hypothesis Repository

```bash
# Navigate to home directory
cd ~

# Clone the Hypothesis server repo
git clone https://github.com/hypothesis/h.git

# Navigate into the repo
cd h

# Check what's there
ls -la
```

You should see a `Dockerfile` and `docker-compose.yml`.

### Step 1.2: Review the docker-compose.yml

```bash
# Take a look at the file
cat docker-compose.yml
```

This file defines all the services needed. We'll modify it to use JFrog.

### Step 1.3: Modify docker-compose.yml for JFrog Proxy

According to John, we need to add `dfa.jfrog.io/docker-proxy/` to image names.

```bash
# Backup the original
cp docker-compose.yml docker-compose.yml.backup

# Edit the file
nano docker-compose.yml
```

**Find and replace image references:**

**BEFORE:**
```yaml
postgres:
  image: postgres:16-alpine
```

**AFTER:**
```yaml
postgres:
  image: dfa.jfrog.io/docker-proxy/postgres:16-alpine
```

**Do this for ALL services:**

- `postgres:` → `dfa.jfrog.io/docker-proxy/postgres:16-alpine`
- `elasticsearch:` → `dfa.jfrog.io/docker-proxy/hypothesis/elasticsearch:elasticsearch7.10`
- `rabbitmq:` → `dfa.jfrog.io/docker-proxy/rabbitmq:3.12-management-alpine`

**IMPORTANT**: The `hypothesis` service (the main app) will be built locally, so leave its `build: .` directive as-is. Don't change it to an image.

Here's what your modified docker-compose.yml should look like:

```yaml
version: '3'

services:
  postgres:
    image: dfa.jfrog.io/docker-proxy/postgres:16-alpine
    ports:
      - "127.0.0.1:5432:5432"
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 3s
      start_period: 1m

  elasticsearch:
    image: dfa.jfrog.io/docker-proxy/hypothesis/elasticsearch:elasticsearch7.10
    ports:
      - "127.0.0.1:9200:9200"
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    healthcheck:
      test: curl --fail --silent http://localhost:9200 >/dev/null
      interval: 3s
      start_period: 1m

  rabbit:
    image: dfa.jfrog.io/docker-proxy/rabbitmq:3.12-management-alpine
    ports:
      - "127.0.0.1:5672:5672"
      - "127.0.0.1:15672:15672"
    healthcheck:
      test: rabbitmq-diagnostics -q ping
      interval: 3s
      start_period: 1m

  # This service will be BUILT locally (not pulled)
  hypothesis:
    build: .
    ports:
      - "0.0.0.0:5000:5000"
    environment:
      - BROKER_URL=amqp://guest:guest@rabbit:5672//
      - DATABASE_URL=postgresql://postgres:postgres@postgres/postgres
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - SECRET_KEY=notasecret
    depends_on:
      postgres:
        condition: service_healthy
      elasticsearch:
        condition: service_healthy
      rabbit:
        condition: service_healthy
    command: ["sh", "-c", "hypothesis init && supervisord -c conf/supervisord.conf"]

volumes:
  postgres-data:
  elasticsearch-data:

networks:
  default:
    name: hypothesis-network
```

**Save and exit** (Ctrl+X, Y, Enter)

### Step 1.4: Build the Hypothesis Image Locally

```bash
# Make sure you're in the h directory
cd ~/h

# Build the Hypothesis Docker image
# This will take 5-10 minutes the first time
docker build -t hypothesis-local:latest .
```

You'll see a lot of output. Wait for it to finish.

### Step 1.5: Update docker-compose.yml to Use Your Built Image

```bash
nano docker-compose.yml
```

**Change the hypothesis service from:**
```yaml
hypothesis:
  build: .
```

**To:**
```yaml
hypothesis:
  image: hypothesis-local:latest
```

This tells docker-compose to use the image you just built.

**Save and exit** (Ctrl+X, Y, Enter)

---

## 🚀 Part 2: Start Hypothesis Services

### Step 2.1: Pull Supporting Images from JFrog

```bash
cd ~/h

# Pull postgres, elasticsearch, rabbitmq from JFrog proxy
docker-compose pull postgres elasticsearch rabbit
```

This should work now with the `dfa.jfrog.io/docker-proxy/` prefix!

### Step 2.2: Start All Services

```bash
# Start everything in detached mode
docker-compose up -d

# Wait about 30 seconds for services to initialize
sleep 30

# Check status
docker-compose ps
```

All services should show "Up (healthy)".

### Step 2.3: Check Logs

```bash
# View all logs
docker-compose logs -f

# Or view just Hypothesis logs
docker-compose logs -f hypothesis
```

Press Ctrl+C to exit logs.

### Step 2.4: Verify Hypothesis is Running

```bash
# Test the API
curl http://localhost:5000/api/

# Or open in browser
# http://localhost:5000
```

You should see the Hypothesis interface!

---

## 👥 Part 3: Create User Accounts

### Step 3.1: Initialize Database

```bash
cd ~/h

# Access the hypothesis container
docker-compose exec hypothesis sh

# Inside the container, initialize
hypothesis init

# Exit the container
exit
```

### Step 3.2: Create Admin User

```bash
# Create your admin account
docker-compose exec hypothesis sh -c "hypothesis user add"

# Follow prompts:
# Username: yourusername
# Email: you@company.com  
# Password: ****

# Make yourself admin
docker-compose exec hypothesis sh -c "hypothesis user admin yourusername"
```

### Step 3.3: Create Second User (Colleague)

```bash
# Create colleague's account
docker-compose exec hypothesis sh -c "hypothesis user add"

# Follow prompts for their info
```

### Step 3.4: Test Login

Open browser: `http://localhost:5000`

Click "Log in" and use your credentials.

---

## 📚 Part 4: Integrate with MyST Documentation

### Background: MyST + Sphinx

**Important**: MyST (Markedly Structured Text) is built **on top of Sphinx**! 

- MyST uses `_config.yml` instead of `conf.py`
- But under the hood, it still generates Sphinx HTML
- So Hypothesis integration works the same way!

### Step 4.1: Find Your MyST Project

```bash
# Navigate to your MyST docs
cd ~/your-myst-project

# You should see _config.yml
ls -la _config.yml
```

### Step 4.2: Add Hypothesis to MyST Config

```bash
nano _config.yml
```

**Add this to your `_config.yml`:**

```yaml
# Hypothesis Integration
sphinx:
  extra_extensions:
    - sphinxcontrib.httpdomain
  config:
    html_js_files:
      - https://hypothes.is/embed.js
      # Or use your local server:
      # - http://YOUR-IP:5000/assets/client/boot.js
```

**For local Hypothesis server**, you can also create a custom template.

### Step 4.3: Create Custom Template for Local Hypothesis

```bash
# Create templates directory in your MyST project
mkdir -p _templates

# Create layout template
nano _templates/layout.html
```

**Add this content:**

```html
{% extends "!layout.html" %}

{% block extrahead %}
{{ super() }}
<script type="application/json" class="js-hypothesis-config">
{
  "services": [{
    "apiUrl": "http://localhost:5000/api/",
    "authority": "localhost"
  }],
  "openSidebar": false
}
</script>
<script async src="http://localhost:5000/assets/client/boot.js"></script>
{% endblock %}
```

**Save and exit** (Ctrl+X, Y, Enter)

### Step 4.4: Update _config.yml to Use Templates

```bash
nano _config.yml
```

**Add:**

```yaml
sphinx:
  config:
    templates_path:
      - _templates
```

**Full example _config.yml:**

```yaml
# Book settings
title: My Documentation
author: Your Team
logo: logo.png

# MyST settings
parse:
  myst_enable_extensions:
    - dollarmath
    - colon_fence

# Sphinx configuration
sphinx:
  extra_extensions:
    - sphinxcontrib.httpdomain
  config:
    templates_path:
      - _templates
    html_js_files:
      - https://hypothes.is/embed.js

# Execution settings
execute:
  execute_notebooks: cache
```

### Step 4.5: Build Your MyST Docs

```bash
cd ~/your-myst-project

# Clean previous builds
jupyter-book clean .

# Build the book
jupyter-book build .

# Or if using myst directly:
# myst build --html
```

### Step 4.6: Serve Your Docs Locally

```bash
# Navigate to build output
cd _build/html

# Serve on port 8080, accessible on local network
python3 -m http.server 8080 --bind 0.0.0.0
```

---

## 🌐 Part 5: Access and Test

### Step 5.1: Get Your IP Address

```bash
# Get WSL IP
hostname -I | awk '{print $1}'

# Or from Windows Command Prompt:
# ipconfig
# Look for "IPv4 Address"
```

Let's say your IP is `192.168.1.100`.

### Step 5.2: Access URLs

**Hypothesis Server:**
- Your computer: `http://localhost:5000`
- Colleague's computer: `http://192.168.1.100:5000`

**Your MyST Docs:**
- Your computer: `http://localhost:8080`
- Colleague's computer: `http://192.168.1.100:8080`

### Step 5.3: Test Annotations

1. **Open your docs**: `http://localhost:8080`
2. **See Hypothesis sidebar** on the right
3. **Log in** with your credentials
4. **Create an annotation** by highlighting text
5. **Have colleague access** `http://YOUR-IP:8080`
6. **They log in** and see your annotation!

---

## 🔄 Daily Workflow

### Morning Startup Script

```bash
nano ~/start-hypothesis.sh
```

**Add:**

```bash
#!/bin/bash
echo "🚀 Starting Hypothesis..."

# Start Hypothesis services
cd ~/h
docker-compose up -d

# Wait for services
sleep 15

# Show status
docker-compose ps

# Get IP
MY_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Hypothesis running at: http://${MY_IP}:5000"
echo "📚 Serve your docs and access at: http://${MY_IP}:8080"
echo ""
echo "To serve MyST docs:"
echo "  cd ~/your-myst-project/_build/html"
echo "  python3 -m http.server 8080 --bind 0.0.0.0"
```

**Make executable:**

```bash
chmod +x ~/start-hypothesis.sh
```

### Evening Shutdown Script

```bash
nano ~/stop-hypothesis.sh
```

**Add:**

```bash
#!/bin/bash
echo "🛑 Stopping Hypothesis..."

cd ~/h
docker-compose down

echo "✅ Services stopped!"
```

**Make executable:**

```bash
chmod +x ~/stop-hypothesis.sh
```

### Usage

```bash
# Morning
~/start-hypothesis.sh

# Serve your docs
cd ~/your-myst-project/_build/html
python3 -m http.server 8080 --bind 0.0.0.0

# Evening
~/stop-hypothesis.sh
```

---

## 🐛 Troubleshooting

### Issue: "Cannot pull image from JFrog"

**Solution:**

```bash
# Re-login to JFrog
docker login dfa.jfrog.io
# Enter credentials

# Try pulling manually
docker pull dfa.jfrog.io/docker-proxy/postgres:16-alpine

# If this works, then docker-compose should too
```

### Issue: "Hypothesis build fails"

**Solution:**

```bash
# Check if you have enough disk space
df -h

# Check Docker is running
docker ps

# Try building with verbose output
docker build -t hypothesis-local:latest . --progress=plain

# Check logs for specific errors
```

### Issue: "Service unhealthy"

**Solution:**

```bash
# Check specific service
docker-compose logs postgres
docker-compose logs elasticsearch

# Elasticsearch often needs more memory
# Check Docker Desktop → Settings → Resources → Memory
# Increase to at least 4GB
```

### Issue: "Hypothesis sidebar doesn't appear"

**Solution:**

```bash
# Open browser DevTools (F12)
# Check Console tab for errors
# Check Network tab - is boot.js loading?

# Try using public Hypothesis first to test
# In _templates/layout.html, change to:
# <script async src="https://hypothes.is/embed.js"></script>

# If that works, local server is the issue
```

### Issue: "Can't access from colleague's computer"

**Solution:**

```bash
# Windows Firewall might be blocking
# Ask IT to allow ports 5000 and 8080

# Or test on same machine first:
# Open two different browsers (Chrome + Firefox)
# Log in as different users
# Both access http://localhost:8080
```

---

## 📝 Quick Reference Commands

```bash
# Start services
cd ~/h && docker-compose up -d

# Stop services
cd ~/h && docker-compose down

# View logs
docker-compose logs -f hypothesis

# Restart hypothesis
docker-compose restart hypothesis

# Create new user
docker-compose exec hypothesis sh -c "hypothesis user add"

# Access PostgreSQL
docker-compose exec postgres psql -U postgres

# Rebuild hypothesis image
cd ~/h
docker build -t hypothesis-local:latest .
docker-compose up -d

# Build MyST docs
cd ~/your-myst-project
jupyter-book build .

# Serve docs
cd ~/your-myst-project/_build/html
python3 -m http.server 8080 --bind 0.0.0.0

# Get your IP
hostname -I | awk '{print $1}'
```

---

## ✅ Success Checklist

- [ ] WSL and Docker installed and running
- [ ] Logged into dfa.jfrog.io Docker registry
- [ ] Cloned hypothesis/h repository
- [ ] Modified docker-compose.yml with JFrog proxy paths
- [ ] Built Hypothesis image locally
- [ ] Pulled supporting images from JFrog
- [ ] Started all services (all healthy)
- [ ] Created admin user account
- [ ] Created second user account
- [ ] Can access Hypothesis at localhost:5000
- [ ] Modified MyST _config.yml
- [ ] Created _templates/layout.html
- [ ] Built MyST docs successfully
- [ ] Served docs at localhost:8080
- [ ] Hypothesis sidebar appears on docs
- [ ] Can create annotations
- [ ] Second user can see annotations
- [ ] Created startup/shutdown scripts

---

## 🎯 Demo Preparation

**Before your team arrives:**

1. ✅ Start Hypothesis: `~/start-hypothesis.sh`
2. ✅ Rebuild MyST docs: `cd ~/your-myst-project && jupyter-book build .`
3. ✅ Serve docs: `cd _build/html && python3 -m http.server 8080 --bind 0.0.0.0`
4. ✅ Get your IP: `hostname -I`
5. ✅ Write IP on whiteboard: `http://192.168.1.XXX:8080`
6. ✅ Test with two browsers yourself
7. ✅ Have user credentials ready

**During demo:**
- Show architecture diagram
- Explain JFrog integration (security scanning)
- Show collaborative annotation in action
- Explain use cases (doc feedback, onboarding, etc.)

**Talking points:**
- "All images from company-approved JFrog registry"
- "Real-time collaborative documentation annotation"
- "Works with our existing MyST documentation"
- "No cloud dependencies - fully on-premises"
- "Scalable - just add more users"

---

## 🚀 Next Steps After Successful POC

1. **Get permanent JFrog approval** for Hypothesis images
2. **Set up HTTPS** with nginx reverse proxy
3. **Integrate with SSO** (if available)
4. **Configure backup** for PostgreSQL data
5. **Set up monitoring** and logging
6. **Document** for team wiki
7. **Train team** on annotation best practices

---

## 🎉 You're All Set!

**Your workflow:**
1. Morning: `~/start-hypothesis.sh`
2. Serve docs: `cd ~/docs/_build/html && python3 -m http.server 8080 --bind 0.0.0.0`
3. Share: `http://YOUR-IP:8080`
4. Annotate and collaborate!
5. Evening: `~/stop-hypothesis.sh`

**Key URLs:**
- Hypothesis: `http://YOUR-IP:5000`
- Your docs: `http://YOUR-IP:8080`
- RabbitMQ Admin: `http://localhost:15672` (guest/guest)

Good luck with your POC! 🚀

---

*Last updated: February 2026*
*Compatible with: Windows 11, WSL2, Ubuntu 22.04+, MyST, JFrog Artifactory*
