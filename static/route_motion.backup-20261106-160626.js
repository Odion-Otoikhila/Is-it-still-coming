/* Route-aware bus movement: never extrapolate in a straight line. */
window.RouteMotion = (() => {
    const vehicles = new Map();
    const shapes = new Map();
    const DEG = Math.PI / 180;
    const MAX_SPEED = 25;          // m/s (90 km/h)
    const MAX_PREDICTION = 32;     // seconds after latest GPS observation
    const SNAP_LIMIT = 150;       // GPS must be <= 150 metres from the route

    function metres(a, b) {
        const lat = ((a.lat + b.lat) / 2) * DEG;
        return Math.hypot((b.lng - a.lng) * 111320 * Math.cos(lat),
                          (b.lat - a.lat) * 111320);
    }

    function closestOnShape(points, loc) {
        let best = {error: Infinity, along: 0};
        let accumulated = 0;
        for (let i = 1; i < points.length; i++) {
            const a = {lat: points[i-1][0], lng: points[i-1][1]};
            const b = {lat: points[i][0], lng: points[i][1]};
            const cosine = Math.cos(loc.lat * DEG);
            const dx = (b.lng - a.lng) * 111320 * cosine;
            const dy = (b.lat - a.lat) * 111320;
            const px = (loc.lng - a.lng) * 111320 * cosine;
            const py = (loc.lat - a.lat) * 111320;
            const squared = dx * dx + dy * dy;
            const t = squared ? Math.max(0, Math.min(1, (px*dx+py*dy)/squared)) : 0;
            const error = Math.hypot(px-t*dx, py-t*dy);
            const length = metres(a,b);
            if (error < best.error) best = {error, along: accumulated+t*length};
            accumulated += length;
        }
        return best;
    }

    function atDistance(points, along) {
        let remaining = Math.max(0,along);
        for (let i=1;i<points.length;i++) {
            const a={lat:points[i-1][0],lng:points[i-1][1]};
            const b={lat:points[i][0],lng:points[i][1]};
            const segment=metres(a,b);
            if (remaining <= segment && segment > 0) {
                const fraction=remaining/segment;
                return [a.lat+(b.lat-a.lat)*fraction, a.lng+(b.lng-a.lng)*fraction];
            }
            remaining -= segment;
        }
        return points[points.length-1];
    }

    function getShape(trip) {
        if (!shapes.has(trip)) {
            shapes.set(trip, fetch('/api/shape/' + encodeURIComponent(trip))
                .then(r => r.ok ? r.json() : null)
                .then(data => data?.points?.length > 1 ? data.points : null)
                .catch(() => null));
        }
        return shapes.get(trip);
    }

    function observe(id, marker, bus) {
        const now = Date.now();
        const raw = {lat:Number(bus.lat), lng:Number(bus.lon)};
        const trip = String(bus.trip_id || '');
        if (!Number.isFinite(raw.lat) || !Number.isFinite(raw.lng)) return;
        const timestamp=Number(bus.timestamp);
        const sampleTime=Number.isFinite(timestamp) && timestamp > 0
            ? timestamp * 1000 : now;
        const prev=vehicles.get(id);
        if (prev && prev.trip === trip && sampleTime < prev.sampleTime) return;
        if (prev && prev.trip === trip && sampleTime <= prev.sampleTime &&
            raw.lat === prev.raw.lat && raw.lng === prev.raw.lng) return;
        const state=prev && prev.trip === trip ? prev : {};
        const oldAlong=state.along;
        const oldTime=state.sampleTime;
        Object.assign(state, {marker, trip, raw, sampleTime, receivedAt:now});
        const reportedSpeed = bus.speed !== null && bus.speed !== undefined
            ? Number(bus.speed) : NaN;
        state.speed=Number.isFinite(reportedSpeed) && reportedSpeed >= 0 && reportedSpeed <= MAX_SPEED
            ? reportedSpeed : 0;
        const project = () => {
            if (!state.shape) return;
            const match=closestOnShape(state.shape,raw);
            state.along=match.error<=SNAP_LIMIT ? match.along : null;
            if (state.along !== null && !Number.isFinite(reportedSpeed) &&
                oldAlong !== undefined && oldAlong !== null && oldTime &&
                sampleTime > oldTime) {
                const seconds=(sampleTime-oldTime)/1000;
                const estimate=(state.along-oldAlong)/seconds;
                if (seconds >= 3 && seconds <= 180 && estimate >= 0 && estimate <= MAX_SPEED)
                    state.speed=estimate;
            }
        };
        if (state.shape) project();
        vehicles.set(id,state);
        if (!state.shape && trip && map.getBounds().pad(0.3).contains([raw.lat,raw.lng])) {
            getShape(trip).then(points => {
                if (vehicles.get(id) !== state || !points) return;
                state.shape=points;
                state.receivedAt=Date.now();
                project();
            });
        }
    }

    let previousFrame = 0;
    function frame(now) {
        if (now - previousFrame < 50) {
            requestAnimationFrame(frame);
            return;
        }
        previousFrame = now;
        now = Date.now();
        for (const state of vehicles.values()) {
            if (!map.hasLayer(state.marker)) continue;
            const age=now-state.sampleTime;
            if (!state.shape || state.along === null || state.along === undefined ||
                state.speed < 0.8 || age > 90000 || age < -20000) {
                state.marker.setLatLng([state.raw.lat,state.raw.lng]);
                continue;
            }
            const seconds=Math.max(0, Math.min(MAX_PREDICTION,(now-state.receivedAt)/1000));
            state.marker.setLatLng(atDistance(state.shape,state.along+state.speed*seconds));
        }
        requestAnimationFrame(frame);
    }

    return {
        observe,
        forget: id => vehicles.delete(id),
        start: () => requestAnimationFrame(frame)
    };
})();
