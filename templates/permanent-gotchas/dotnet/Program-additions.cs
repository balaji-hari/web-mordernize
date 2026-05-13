// Add these into the `dotnet new webapi` Program.cs.
// `dotnet new` ships without CORS or /health; both are required for the
// plugin's smoke gate and any UI-to-API call from a fresh scaffold.

// --- Before var app = builder.Build();
const string DevCorsPolicy = "DevCors";
builder.Services.AddCors(o => o.AddPolicy(DevCorsPolicy, p => p
    .WithOrigins(
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4200")
    .AllowAnyHeader()
    .AllowAnyMethod()
    .AllowCredentials()));

// --- After var app = builder.Build();
app.UseCors(DevCorsPolicy);
app.MapGet("/health", () => Results.Ok(new { status = "UP" }));

// --- At the bottom of Program.cs (load-bearing for WebApplicationFactory<Program>):
// public partial class Program { }
