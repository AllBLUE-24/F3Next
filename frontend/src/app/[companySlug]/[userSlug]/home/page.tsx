"use client";

import { use } from "react";
import Link from "next/link";
import { 
  Bot, 
  Database, 
  Server, 
  Settings, 
  FileSpreadsheet, 
  TestTube2, 
  LayoutDashboard,
  ExternalLink
} from "lucide-react";

interface PageProps {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default function HomePage({ params }: PageProps) {
  const { companySlug, userSlug } = use(params);

  // Define the core tools available in F3Next
  const tools = [
    {
      name: "Discovery Agent",
      description: "Initial requirements gathering and project scoping.",
      icon: <Bot className="h-6 w-6 text-blue-400" />,
      href: `/${companySlug}/${userSlug}/discovery`, // Links to the chat we built
      status: "Active",
    },
    {
      name: "ERP Selector",
      description: "AI-driven comparison and recommendation engine.",
      icon: <LayoutDashboard className="h-6 w-6 text-purple-400" />,
      href: "#", // Placeholder
      status: "Coming Soon",
    },
    {
      name: "Data Mapper",
      description: "Import legacy data and map to new ERP schemas.",
      icon: <FileSpreadsheet className="h-6 w-6 text-green-400" />,
      href: "#",
      status: "Locked",
    },
    {
      name: "Testing Suite",
      description: "Automated validation and quality assurance.",
      icon: <TestTube2 className="h-6 w-6 text-orange-400" />,
      href: "#",
      status: "Locked",
    },
  ];

  // Define infrastructure services (External or Admin links)
  const services = [
    {
      name: "AWS Console",
      description: "Manage cloud instances and resources.",
      icon: <Server className="h-5 w-5 text-zinc-400" />,
      href: "https://aws.amazon.com/console/",
      external: true,
    },
    {
      name: "MinIO Storage",
      description: "Object storage bucket management.",
      icon: <Database className="h-5 w-5 text-zinc-400" />,
      href: "#", // Replace with your MinIO console URL
      external: true,
    },
    {
      name: "Instance Settings",
      description: "Configure project-level variables.",
      icon: <Settings className="h-5 w-5 text-zinc-400" />,
      href: "#", 
      external: false,
    },
  ];

  return (
    <div className="p-6 md:p-8 space-y-10 max-w-7xl mx-auto">
      
      {/* 1. Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Mission Control
          </h1>
          <p className="text-zinc-400 mt-1">
            Manage your digital transformation for <span className="text-blue-400 font-medium">{companySlug}</span>.
          </p>
        </div>
        <div className="flex items-center gap-3">
           <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-xs text-zinc-500 font-mono">
             v1.0.0-beta
           </span>
        </div>
      </div>

      {/* 2. Primary Tools Grid */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
          Active Modules
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {tools.map((tool) => (
            <Link 
              key={tool.name} 
              href={tool.href}
              className={`group relative flex flex-col justify-between p-6 rounded-xl border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800/50 transition-all duration-200 ${
                tool.status === "Locked" ? "opacity-50 cursor-not-allowed pointer-events-none" : "hover:border-zinc-700"
              }`}
            >
              <div>
                <div className="mb-4 p-2 inline-block rounded-lg bg-zinc-950 border border-zinc-800 shadow-inner group-hover:scale-110 transition-transform">
                  {tool.icon}
                </div>
                <h3 className="text-lg font-medium text-white group-hover:text-blue-400 transition-colors">
                  {tool.name}
                </h3>
                <p className="mt-2 text-sm text-zinc-400 leading-relaxed">
                  {tool.description}
                </p>
              </div>
              
              <div className="mt-6 flex items-center justify-between">
                <span className={`text-xs px-2 py-1 rounded-full border ${
                  tool.status === "Active" ? "bg-green-500/10 border-green-500/20 text-green-400" :
                  tool.status === "Coming Soon" ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-400" :
                  "bg-zinc-800 border-zinc-700 text-zinc-500"
                }`}>
                  {tool.status}
                </span>
                {tool.status === "Active" && (
                  <span className="text-zinc-600 group-hover:translate-x-1 transition-transform">
                    →
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* 3. Infrastructure & Services Grid */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
          Infrastructure Services
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {services.map((service) => (
            <Link
              key={service.name}
              href={service.href}
              target={service.external ? "_blank" : "_self"}
              className="flex items-center gap-4 p-4 rounded-lg border border-zinc-800 bg-zinc-900/20 hover:bg-zinc-800/40 hover:border-zinc-700 transition-all"
            >
              <div className="p-2 rounded-md bg-zinc-950 border border-zinc-800 text-zinc-400">
                {service.icon}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-medium text-zinc-200">
                    {service.name}
                  </h3>
                  {service.external && (
                    <ExternalLink className="h-3 w-3 text-zinc-600" />
                  )}
                </div>
                <p className="text-xs text-zinc-500">
                  {service.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

    </div>
  );
}